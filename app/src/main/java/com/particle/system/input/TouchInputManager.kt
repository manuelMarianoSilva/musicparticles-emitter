package com.particle.system.input

import android.view.MotionEvent
import android.view.VelocityTracker
import com.particle.system.data.TouchEvent
import com.particle.system.data.TouchEventType
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap

class TouchInputManager(
    private val screenW: Float,
    private val screenH: Float,
    private val deviceId: String,
    private val onTouchEvent: (TouchEvent) -> Unit,
    private val onBurstThreshold: (pointerId: Int, x: Float, y: Float, holdMs: Long) -> Unit
) {
    private data class PointerSession(
        val sessionId: String = UUID.randomUUID().toString(),
        val startMs: Long = System.currentTimeMillis(),
        var trailCount: Int = 0,
        var lastX: Float = 0f,
        var lastY: Float = 0f
    )

    private val sessions    = ConcurrentHashMap<Int, PointerSession>()
    private val burstTimers = ConcurrentHashMap<Int, java.util.Timer>()
    private var velTracker: VelocityTracker? = null

    private val BURST_DELAY_MS    = 300L
    private val BURST_INTERVAL_MS = 400L

    fun getVelocityX(pid: Int): Float {
        velTracker?.computeCurrentVelocity(1)
        return velTracker?.getXVelocity(pid) ?: 0f
    }

    fun getVelocityY(pid: Int): Float {
        velTracker?.computeCurrentVelocity(1)
        return velTracker?.getYVelocity(pid) ?: 0f
    }

    fun getHoldDuration(pid: Int): Long =
        sessions[pid]?.let { System.currentTimeMillis() - it.startMs } ?: 0L

    fun onTouchEvent(event: MotionEvent) {
        if (velTracker == null) velTracker = VelocityTracker.obtain()
        velTracker!!.addMovement(event)

        val idx = event.actionIndex
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN, MotionEvent.ACTION_POINTER_DOWN -> {
                val pid = event.getPointerId(idx)
                val x = event.getX(idx); val y = event.getY(idx)
                val session = PointerSession(lastX = x, lastY = y)
                sessions[pid] = session
                emit(TouchEventType.TOUCH_DOWN, pid, x, y, event.getPressure(idx), session)
                scheduleBursts(pid)
            }
            MotionEvent.ACTION_MOVE -> {
                velTracker!!.computeCurrentVelocity(1)
                for (i in 0 until event.pointerCount) {
                    val pid = event.getPointerId(i)
                    val session = sessions[pid] ?: continue
                    session.trailCount++
                    session.lastX = event.getX(i)
                    session.lastY = event.getY(i)
                    emit(TouchEventType.TOUCH_MOVE, pid, event.getX(i), event.getY(i),
                        event.getPressure(i), session)
                }
            }
            MotionEvent.ACTION_UP, MotionEvent.ACTION_POINTER_UP, MotionEvent.ACTION_CANCEL -> {
                val pid = event.getPointerId(idx)
                val session = sessions[pid] ?: return
                cancelBursts(pid)
                emit(TouchEventType.TOUCH_UP, pid,
                    event.getX(idx), event.getY(idx), event.getPressure(idx), session)
                sessions.remove(pid)
            }
        }
    }

    private fun emit(type: TouchEventType, pid: Int, x: Float, y: Float,
                     pressure: Float, session: PointerSession) {
        velTracker?.computeCurrentVelocity(1)
        val vx = velTracker?.getXVelocity(pid) ?: 0f
        val vy = velTracker?.getYVelocity(pid) ?: 0f
        onTouchEvent(TouchEvent(
            type           = type,
            deviceId       = deviceId,
            sessionId      = session.sessionId,
            pointerId      = pid,
            x              = x / screenW,
            y              = y / screenH,
            pressure       = pressure.coerceIn(0f, 1f),
            holdDurationMs = System.currentTimeMillis() - session.startMs,
            velocityX      = vx / screenW,
            velocityY      = vy / screenH,
            trailLength    = session.trailCount
        ))
    }

    private fun scheduleBursts(pid: Int) {
        val timer = java.util.Timer(true)
        burstTimers[pid] = timer
        timer.schedule(object : java.util.TimerTask() {
            override fun run() {
                val session = sessions[pid] ?: run { cancel(); return }
                val holdMs = System.currentTimeMillis() - session.startMs
                onBurstThreshold(pid, session.lastX, session.lastY, holdMs)
                onTouchEvent(TouchEvent(
                    type           = TouchEventType.TOUCH_BURST,
                    deviceId       = deviceId,
                    sessionId      = session.sessionId,
                    pointerId      = pid,
                    x              = session.lastX / screenW,
                    y              = session.lastY / screenH,
                    pressure       = 1f,
                    holdDurationMs = holdMs,
                    velocityX      = 0f,
                    velocityY      = 0f,
                    trailLength    = session.trailCount
                ))
                // Reschedule manually to avoid scheduleAtFixedRate
                if (sessions.containsKey(pid)) scheduleBursts(pid)
            }
        }, BURST_DELAY_MS)
    }

    private fun cancelBursts(pid: Int) {
        burstTimers[pid]?.cancel()
        burstTimers.remove(pid)
    }

    fun release() {
        velTracker?.recycle()
        velTracker = null
        burstTimers.values.forEach { it.cancel() }
        burstTimers.clear()
        sessions.clear()
    }
}