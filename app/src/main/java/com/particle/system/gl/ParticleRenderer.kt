package com.particle.system.gl

import android.opengl.GLES20
import android.opengl.GLSurfaceView
import android.opengl.Matrix
import com.particle.system.particle.ParticleSystem
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer
import javax.microedition.khronos.egl.EGLConfig
import javax.microedition.khronos.opengles.GL10

class ParticleRenderer(private val ps: ParticleSystem) : GLSurfaceView.Renderer {

    private val VERT = """
        uniform mat4 uMVP;
        attribute vec2 aPos;
        attribute vec4 aColor;
        attribute float aSize;
        varying vec4 vColor;
        void main() {
            gl_Position  = uMVP * vec4(aPos, 0.0, 1.0);
            gl_PointSize = aSize;
            vColor       = aColor;
        }""".trimIndent()

    private val FRAG = """
        precision mediump float;
        varying vec4 vColor;
        void main() {
            vec2 coord = gl_PointCoord - vec2(0.5);
            float dist = length(coord);
            float alpha = smoothstep(0.5, 0.1, dist);
            if (alpha < 0.01) discard;
            gl_FragColor = vec4(vColor.rgb, vColor.a * alpha);
        }""".trimIndent()

    private lateinit var shader: ShaderProgram
    private var vboId = 0
    private var aPos = 0; private var aColor = 0
    private var aSize = 0; private var uMVP = 0
    private val mvp = FloatArray(16)

    private val STRIDE   = 7
    private val MAX_PART = 12_000
    private val vData    = FloatArray(MAX_PART * STRIDE)
    private lateinit var vBuf: FloatBuffer

    private var lastMs = System.currentTimeMillis()

    override fun onSurfaceCreated(gl: GL10?, config: EGLConfig?) {
        GLES20.glClearColor(0f, 0f, 0.04f, 1f)
        GLES20.glEnable(GLES20.GL_BLEND)
        GLES20.glBlendFunc(GLES20.GL_SRC_ALPHA, GLES20.GL_ONE)

        shader = ShaderProgram(VERT, FRAG)
        aPos   = shader.attrib("aPos")
        aColor = shader.attrib("aColor")
        aSize  = shader.attrib("aSize")
        uMVP   = shader.uniform("uMVP")

        val ids = IntArray(1)
        GLES20.glGenBuffers(1, ids, 0)
        vboId = ids[0]

        vBuf = ByteBuffer.allocateDirect(MAX_PART * STRIDE * 4)
            .order(ByteOrder.nativeOrder()).asFloatBuffer()
    }

    override fun onSurfaceChanged(gl: GL10?, w: Int, h: Int) {
        GLES20.glViewport(0, 0, w, h)
        Matrix.orthoM(mvp, 0, 0f, w.toFloat(), h.toFloat(), 0f, -1f, 1f)
    }

    override fun onDrawFrame(gl: GL10?) {
        val now = System.currentTimeMillis()
        val dt  = (now - lastMs).coerceIn(1, 32).toFloat()
        lastMs  = now

        ps.update(dt)
        GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT)

        val count: Int
        synchronized(ps) {
            val particles = ps.liveParticles
            count = particles.size.coerceAtMost(MAX_PART)
            var off = 0
            for (i in 0 until count) {
                val p = particles[i]
                val a = p.life.coerceIn(0f, 1f)
                vData[off++] = p.x;  vData[off++] = p.y
                vData[off++] = p.r;  vData[off++] = p.g
                vData[off++] = p.b;  vData[off++] = a
                vData[off++] = p.size * a
            }
        }
        if (count == 0) return

        vBuf.position(0)
        vBuf.put(vData, 0, count * STRIDE)
        vBuf.position(0)

        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, vboId)
        GLES20.glBufferData(GLES20.GL_ARRAY_BUFFER, count * STRIDE * 4, vBuf, GLES20.GL_DYNAMIC_DRAW)

        shader.use()
        GLES20.glUniformMatrix4fv(uMVP, 1, false, mvp, 0)

        val sb = STRIDE * 4
        GLES20.glEnableVertexAttribArray(aPos)
        GLES20.glVertexAttribPointer(aPos,   2, GLES20.GL_FLOAT, false, sb, 0)
        GLES20.glEnableVertexAttribArray(aColor)
        GLES20.glVertexAttribPointer(aColor, 4, GLES20.GL_FLOAT, false, sb, 2 * 4)
        GLES20.glEnableVertexAttribArray(aSize)
        GLES20.glVertexAttribPointer(aSize,  1, GLES20.GL_FLOAT, false, sb, 6 * 4)

        GLES20.glDrawArrays(GLES20.GL_POINTS, 0, count)

        GLES20.glDisableVertexAttribArray(aPos)
        GLES20.glDisableVertexAttribArray(aColor)
        GLES20.glDisableVertexAttribArray(aSize)
        GLES20.glBindBuffer(GLES20.GL_ARRAY_BUFFER, 0)
    }
}