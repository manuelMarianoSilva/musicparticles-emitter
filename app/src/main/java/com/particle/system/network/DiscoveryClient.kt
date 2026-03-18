package com.particle.system.network

import kotlinx.coroutines.*
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress
import org.json.JSONObject

/**
 * Broadcasts DISCOVER packets every second on port 9877.
 * When an ACK is received from a receiver, stores its IP
 * and notifies [onReceiverFound] so BroadcastServer can
 * switch to unicast.
 */
class DiscoveryClient(
    private val onReceiverFound: (ip: String) -> Unit,
    private val onReceiverLost: () -> Unit,
    private val discoveryPort: Int = 9877
) {
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var socket: DatagramSocket? = null

    @Volatile var receiverIp: String? = null
    @Volatile var lastAckMs: Long = 0L

//    private val BROADCAST_IP      = "255.255.255.255"
    private val DISCOVER_INTERVAL = 1000L
    private val RECEIVER_TIMEOUT  = 3000L

    fun start(localIp: String) {
        // Separate socket for listening to ACKs
        val listenSocket = DatagramSocket(null).apply {
            reuseAddress = true
            bind(java.net.InetSocketAddress(discoveryPort))
        }
        socket = listenSocket

        // Listen for ACK and HEARTBEAT responses
        scope.launch {
            val buf    = ByteArray(1024)
            val packet = DatagramPacket(buf, buf.size)
            while (isActive) {
                try {
                    listenSocket.receive(packet)
                    val json = JSONObject(String(packet.data, 0, packet.length, Charsets.UTF_8))
                    when (json.optString("type")) {
                        "ACK" -> {
                            val ip = json.getString("senderIp")
                            lastAckMs = System.currentTimeMillis()
                            android.util.Log.d("DiscoveryClient", "ACK received, ip=$ip, current receiverIp=$receiverIp")
                            if (receiverIp != ip) {
                                android.util.Log.d("DiscoveryClient", "Calling onReceiverFound with $ip")
                                onReceiverFound(ip)
                                receiverIp = ip
                                android.util.Log.d("DiscoveryClient", "onReceiverFound completed, receiverIp set to $ip")
                            }
                        }
                        "HEARTBEAT" -> {
                            lastAckMs = System.currentTimeMillis()
                        }
                    }
                } catch (e: Exception) {
                    if (isActive) android.util.Log.w("DiscoveryClient", "Receive error: ${e.message}")
                }
            }
        }

        // Separate socket for broadcasting DISCOVER
        scope.launch {
            val sendSocket = DatagramSocket().apply { broadcast = true }
            val broadcastAddr = InetAddress.getByName(getSubnetBroadcast(localIp))
            android.util.Log.d("DiscoveryClient", "Broadcasting to ${broadcastAddr.hostAddress}")
            while (isActive) {
                try {
                    val json  = JSONObject().apply {
                        put("type", "DISCOVER")
                        put("senderIp", localIp)
                    }.toString()
                    val bytes  = json.toByteArray(Charsets.UTF_8)
                    val packet = DatagramPacket(bytes, bytes.size, broadcastAddr, discoveryPort)
                    sendSocket.send(packet)
                    android.util.Log.d("DiscoveryClient", "Sent DISCOVER")
                } catch (e: Exception) {
                    android.util.Log.w("DiscoveryClient", "Send error: ${e.message}")
                }
                delay(DISCOVER_INTERVAL)
            }
            sendSocket.close()
        }

        // Monitor receiver timeout
        scope.launch {
            while (isActive) {
                delay(RECEIVER_TIMEOUT)
                val age = System.currentTimeMillis() - lastAckMs
                if (receiverIp != null && age > RECEIVER_TIMEOUT) {
                    android.util.Log.d("DiscoveryClient", "Receiver lost")
                    receiverIp = null
                    onReceiverLost()
                }
            }
        }
    }
    fun stop() {
        scope.cancel()
        socket?.close()
        socket = null
    }

    private fun getSubnetBroadcast(localIp: String): String {
        val parts = localIp.split(".")
        return if (parts.size == 4) "${parts[0]}.${parts[1]}.${parts[2]}.255"
        else "255.255.255.255"
    }
}