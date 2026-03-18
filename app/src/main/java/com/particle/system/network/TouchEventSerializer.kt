package com.particle.system.network

import com.particle.system.data.TouchEvent
import com.particle.system.data.TouchEventType
import org.json.JSONObject

object TouchEventSerializer {

    fun toJson(e: TouchEvent): String = JSONObject().run {
        put("type",    e.type.name)
        put("did",     e.deviceId)
        put("sid",     e.sessionId)
        put("pid",     e.pointerId)
        put("x",       e.x.toDouble())
        put("y",       e.y.toDouble())
        put("pr",      e.pressure.toDouble())
        put("holdMs",  e.holdDurationMs)
        put("vx",      e.velocityX.toDouble())
        put("vy",      e.velocityY.toDouble())
        put("trail",   e.trailLength)
        put("ts",      e.timestamp)
        toString()
    }

    fun fromJson(json: String): TouchEvent {
        val o = JSONObject(json)
        return TouchEvent(
            type           = TouchEventType.valueOf(o.getString("type")),
            deviceId       = o.getString("did"),
            sessionId      = o.getString("sid"),
            pointerId      = o.getInt("pid"),
            x              = o.getDouble("x").toFloat(),
            y              = o.getDouble("y").toFloat(),
            pressure       = o.getDouble("pr").toFloat(),
            holdDurationMs = o.getLong("holdMs"),
            velocityX      = o.getDouble("vx").toFloat(),
            velocityY      = o.getDouble("vy").toFloat(),
            trailLength    = o.getInt("trail"),
            timestamp      = o.getLong("ts")
        )
    }
}