package com.particle.system.gl

import android.opengl.GLES20

class ShaderProgram(vertSrc: String, fragSrc: String) {

    val id: Int

    init {
        val vert = compile(GLES20.GL_VERTEX_SHADER, vertSrc)
        val frag = compile(GLES20.GL_FRAGMENT_SHADER, fragSrc)
        id = GLES20.glCreateProgram().also { prog ->
            GLES20.glAttachShader(prog, vert)
            GLES20.glAttachShader(prog, frag)
            GLES20.glLinkProgram(prog)
            GLES20.glDeleteShader(vert)
            GLES20.glDeleteShader(frag)
        }
    }

    fun use() = GLES20.glUseProgram(id)
    fun attrib(name: String)  = GLES20.glGetAttribLocation(id, name)
    fun uniform(name: String) = GLES20.glGetUniformLocation(id, name)

    private fun compile(type: Int, src: String): Int {
        val shader = GLES20.glCreateShader(type)
        GLES20.glShaderSource(shader, src)
        GLES20.glCompileShader(shader)
        val status = IntArray(1)
        GLES20.glGetShaderiv(shader, GLES20.GL_COMPILE_STATUS, status, 0)
        if (status[0] == 0) {
            val log = GLES20.glGetShaderInfoLog(shader)
            GLES20.glDeleteShader(shader)
            error("Shader compile error: $log")
        }
        return shader
    }
}