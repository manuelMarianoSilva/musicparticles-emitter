package com.particle.system.network

import com.particle.system.data.TouchEvent
import kotlinx.coroutines.*
import kotlinx.coroutines.channels.Channel
import java.net.DatagramPacket
import java.net.DatagramSocket
import java.net.InetAddress

/**
 * Sends TouchEvents as unicast UDP packets directly to the receiver's IP.
 * Waits for DiscoveryClient to find a receiver before sending anything.
 * Sends a HEARTBEAT every 500ms to keep the connection alive.
 */
class BroadcastServer(
    private val port: Int = 9876,
    private val heartbeatPort: Int = 9877
) {
    private val scope   = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val channel = Channel<TouchEvent>(Channel.BUFFERED)

    private var socket: DatagramSocket? = null

    @Volatile private var targetIp: String? = null

    private val HEARTBEAT_INTERVAL = 500L

    fun start() {
        socket = DatagramSocket().apply {
            broadcast = true
            reuseAddress = true
        }

        // Drain channel and send touch events via unicast
        scope.launch {
            for (e in channel) {
                val ip = targetIp ?: continue
                try {
                    val bytes  = TouchEventSerializer.toJson(e).toByteArray(Charsets.UTF_8)
                    val target = InetAddress.getByName(ip)
                    socket?.send(DatagramPacket(bytes, bytes.size, target, port))
                } catch (ex: Exception) {
                    android.util.Log.w("BroadcastServer", "Send failed: ${ex.message}")
                }
            }
        }

        // Heartbeat loop
        scope.launch {
            while (isActive) {
                val ip = targetIp
                if (ip != null) {
                    try {
                        val json   = """{"type":"HEARTBEAT"}""".toByteArray(Charsets.UTF_8)
                        val target = InetAddress.getByName(ip)
                        socket?.send(DatagramPacket(json, json.size, target, heartbeatPort))
                    } catch (ex: Exception) {
                        android.util.Log.w("BroadcastServer", "Heartbeat failed: ${ex.message}")
                    }
                }
                delay(HEARTBEAT_INTERVAL)
            }
        }
    }

    fun enqueue(e: TouchEvent) { channel.trySend(e) }

    fun setReceiverIp(ip: String) {
        android.util.Log.d("BroadcastServer", "Receiver IP set to $ip")
        targetIp = ip
    }

    fun clearReceiverIp() {
        android.util.Log.d("BroadcastServer", "Receiver IP cleared")
        targetIp = null
    }

    fun stop() {
        scope.cancel()
        channel.close()
        socket?.close()
        socket = null
    }
}