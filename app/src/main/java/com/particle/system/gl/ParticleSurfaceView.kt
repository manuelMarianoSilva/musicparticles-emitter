package com.particle.system.gl

import android.content.Context
import android.opengl.GLSurfaceView
import android.view.MotionEvent
import com.particle.system.input.TouchInputManager
import com.particle.system.particle.ParticleEmitter
import com.particle.system.particle.ParticleSystem

class ParticleSurfaceView(
    context: Context,
    private val inputManager: TouchInputManager,
    private val onTouchDown: ((normX: Float, normY: Float) -> Unit)? = null
) : GLSurfaceView(context) {
    private var lastTouchX = 0f
    private var lastTouchY = 0f
    val particleSystem = ParticleSystem(20_000)
    val emitter = ParticleEmitter(particleSystem)
    val renderer: ParticleRenderer

    private var screenW = 1f
    private var screenH = 1f

    init {
        setEGLContextClientVersion(2)
        renderer = ParticleRenderer(particleSystem)
        setRenderer(renderer)
        renderMode = RENDERMODE_CONTINUOUSLY
    }

    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        super.onSizeChanged(w, h, oldw, oldh)
        screenW = w.toFloat()
        screenH = h.toFloat()
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        inputManager.onTouchEvent(event)

        val idx = event.actionIndex
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN, MotionEvent.ACTION_POINTER_DOWN -> {
                val x = event.getX(idx)
                val y = event.getY(idx)
                val pressure = event.getPressure(idx)
                onTouchDown?.invoke(x / screenW, y / screenH)
                queueEvent { emitter.onTouchDown(x, y, pressure) }
            }
            MotionEvent.ACTION_MOVE -> {
                for (i in 0 until event.pointerCount) {
                    val x = event.getX(i)
                    val y = event.getY(i)
                    val pid = event.getPointerId(i)
                    val vx = inputManager.getVelocityX(pid)
                    val vy = inputManager.getVelocityY(pid)

                    // Interpolate between last and current position
                    val dx = x - lastTouchX
                    val dy = y - lastTouchY
                    val dist = kotlin.math.sqrt(dx * dx + dy * dy)
                    val steps = (dist / 8f).toInt().coerceIn(1, 20)

                    for (step in 0..steps) {
                        val t = step.toFloat() / steps
                        val ix = lastTouchX + dx * t
                        val iy = lastTouchY + dy * t
                        queueEvent { emitter.onTouchMove(ix, iy, vx, vy) }
                    }

                    lastTouchX = x
                    lastTouchY = y
                }
            }
            MotionEvent.ACTION_UP, MotionEvent.ACTION_POINTER_UP -> {
                val x = event.getX(idx)
                val y = event.getY(idx)
                val holdMs = inputManager.getHoldDuration(event.getPointerId(idx))
                queueEvent { emitter.onTouchUp(x, y, holdMs) }
            }
        }
        return true
    }
}