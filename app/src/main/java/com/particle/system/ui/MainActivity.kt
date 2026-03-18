package com.particle.system.ui

import android.os.Bundle
import android.view.View
import android.view.WindowManager
import androidx.appcompat.app.AppCompatActivity
import com.particle.system.gl.ParticleSurfaceView
import com.particle.system.input.TouchInputManager
import com.particle.system.network.BroadcastServer
import com.particle.system.network.DiscoveryClient
import java.net.NetworkInterface

class MainActivity : AppCompatActivity() {

    private lateinit var surfaceView: ParticleSurfaceView
    private lateinit var server: BroadcastServer
    private lateinit var inputManager: TouchInputManager
    private lateinit var discoveryClient: DiscoveryClient

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        @Suppress("DEPRECATION")
        window.decorView.systemUiVisibility = (
                View.SYSTEM_UI_FLAG_FULLSCREEN or
                        View.SYSTEM_UI_FLAG_HIDE_NAVIGATION or
                        View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                )

        val dm = resources.displayMetrics
        val sw = dm.widthPixels.toFloat()
        val sh = dm.heightPixels.toFloat()

        val prefs = getSharedPreferences("particle_prefs", MODE_PRIVATE)
        val deviceId = prefs.getString("device_id", null) ?: run {
            java.util.UUID.randomUUID().toString().also {
                prefs.edit().putString("device_id", it).apply()
            }
        }
        android.util.Log.d("DeviceID", "This device ID is: $deviceId")

        server = BroadcastServer(port = 9876).also { it.start() }

        discoveryClient = DiscoveryClient(
            onReceiverFound = { ip ->
                android.util.Log.d("MainActivity", "Receiver found at $ip")
                server.setReceiverIp(ip)
            },
            onReceiverLost = {
                android.util.Log.d("MainActivity", "Receiver lost")
                server.clearReceiverIp()
            }
        )

        val localIp = getLocalIpAddress() ?: "0.0.0.0"
        android.util.Log.d("MainActivity", "Local IP: $localIp")
        discoveryClient.start(localIp)

        inputManager = TouchInputManager(
            screenW  = sw,
            screenH  = sh,
            deviceId = deviceId,
            onTouchEvent = { server.enqueue(it) },
            onBurstThreshold = { _, x, y, holdMs ->
                surfaceView.queueEvent {
                    surfaceView.emitter.onBurst(x, y, holdMs)
                }
            }
        )

        surfaceView = ParticleSurfaceView(this, inputManager)
        setContentView(surfaceView)
    }

    private fun getLocalIpAddress(): String? {
        return try {
            NetworkInterface.getNetworkInterfaces()
                .asSequence()
                .flatMap { it.inetAddresses.asSequence() }
                .firstOrNull { !it.isLoopbackAddress && it.hostAddress?.contains('.') == true }
                ?.hostAddress
        } catch (e: Exception) {
            android.util.Log.w("MainActivity", "Could not get IP: ${e.message}")
            null
        }
    }

    override fun onResume()  { super.onResume();  surfaceView.onResume() }
    override fun onPause()   { super.onPause();   surfaceView.onPause() }
    override fun onDestroy() {
        super.onDestroy()
        discoveryClient.stop()
        server.stop()
        inputManager.release()
    }
}