package com.particle.system.ui

import android.animation.ValueAnimator
import android.content.Context
import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.RectF
import android.view.View
import com.particle.system.R

class NoteGridView(context: Context) : View(context) {

    private val CHROMATIC_NOTES   = arrayOf("C","C#","D","D#","E","F","F#","G","G#","A","A#","B")
    private val CHROMATIC_OCTAVES = arrayOf("4", "3", "2")
    private val SHARP_NOTES       = setOf(1, 3, 6, 8, 10)

    private val ONESHOT_GRID = arrayOf(
        arrayOf("A4", "D5"),
        arrayOf("B3", "E4"),
        arrayOf("D3", "G3"),
        arrayOf("E2", "A2")
    )

    private val BASS_GRID = arrayOf(
        arrayOf("D2", "G2"),
        arrayOf("E1", "A1")
    )

    var chromaticMode = false
    var bassMode      = false
    var drumMode      = false

    private val gridLinePaint = Paint().apply {
        color = 0x26FFFFFF.toInt()
        strokeWidth = 1.5f
        style = Paint.Style.STROKE
        isAntiAlias = true
    }

    private val octaveDividerPaint = Paint().apply {
        color = 0x40FFFFFF.toInt()
        strokeWidth = 2.5f
        style = Paint.Style.STROKE
        isAntiAlias = true
    }

    private val sharpCellPaint = Paint().apply {
        color = 0x15000000.toInt()
        style = Paint.Style.FILL
    }

    private val labelPaint = Paint().apply {
        color = 0x55FFFFFF.toInt()
        textSize = 32f
        typeface = android.graphics.Typeface.MONOSPACE
        textAlign = Paint.Align.CENTER
        isAntiAlias = true
    }

    private val highlightPaint = Paint().apply {
        color = 0x99FFFFFF.toInt()
        style = Paint.Style.FILL
        isAntiAlias = true
    }

    private val highlights = mutableMapOf<Pair<Int, Int>, Int>()
    private val animators  = mutableMapOf<Pair<Int, Int>, ValueAnimator>()

    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        when {
            chromaticMode -> drawChromaticGrid(canvas)
            bassMode      -> drawBassGrid(canvas)
            drumMode      -> drawDrumGrid(canvas)
            else          -> drawOneShotGrid(canvas)
        }
    }

    private fun drawChromaticGrid(canvas: Canvas) {
        val w    = width.toFloat()
        val h    = height.toFloat()
        val colW = w / 12f
        val rowH = h / 3f
        for (row in 0..2) {
            for (col in 0..11) {
                val rect = RectF(col * colW, row * rowH, (col + 1) * colW, (row + 1) * rowH)
                if (col in SHARP_NOTES) canvas.drawRect(rect, sharpCellPaint)
                drawHighlight(canvas, row, col, rect)
            }
        }
        for (col in 1..11) canvas.drawLine(col * colW, 0f, col * colW, h, gridLinePaint)
        for (row in 1..2) canvas.drawLine(0f, row * rowH, w, row * rowH, octaveDividerPaint)
        for (row in 0..2) {
            for (col in 0..11) {
                val cx  = col * colW + colW / 2f
                val cy  = row * rowH + rowH / 2f
                val lbl = "${CHROMATIC_NOTES[col]}${CHROMATIC_OCTAVES[row]}"
                canvas.drawText(lbl, cx, cy - (labelPaint.descent() + labelPaint.ascent()) / 2f, labelPaint)
            }
        }
    }

    private fun drawOneShotGrid(canvas: Canvas) {
        val w    = width.toFloat()
        val h    = height.toFloat()
        val colW = w / 2f
        val rowH = h / 4f
        for (row in 0..3) {
            for (col in 0..1) {
                val rect = RectF(col * colW, row * rowH, (col + 1) * colW, (row + 1) * rowH)
                drawHighlight(canvas, row, col, rect)
                val lbl = ONESHOT_GRID[row][col]
                val cx  = col * colW + colW / 2f
                val cy  = row * rowH + rowH / 2f
                canvas.drawText(lbl, cx, cy - (labelPaint.descent() + labelPaint.ascent()) / 2f, labelPaint)
            }
        }
        canvas.drawLine(colW, 0f, colW, h, octaveDividerPaint)
        for (row in 1..3) canvas.drawLine(0f, row * rowH, w, row * rowH, gridLinePaint)
    }

    private fun drawBassGrid(canvas: Canvas) {
        val w    = width.toFloat()
        val h    = height.toFloat()
        val colW = w / 2f
        val rowH = h / 2f
        for (row in 0..1) {
            for (col in 0..1) {
                val rect = RectF(col * colW, row * rowH, (col + 1) * colW, (row + 1) * rowH)
                drawHighlight(canvas, row, col, rect)
                val lbl = BASS_GRID[row][col]
                val cx  = col * colW + colW / 2f
                val cy  = row * rowH + rowH / 2f
                canvas.drawText(lbl, cx, cy - (labelPaint.descent() + labelPaint.ascent()) / 2f, labelPaint)
            }
        }
        canvas.drawLine(colW, 0f, colW, h, octaveDividerPaint)
        canvas.drawLine(0f, rowH, w, rowH, gridLinePaint)
    }

    private fun drawDrumGrid(canvas: Canvas) {
        val w      = width.toFloat()
        val h      = height.toFloat()
        val row1Top = h * 0.33f
        val row2Top = h * 0.66f
        val row3Top = h * 0.85f
        val midX    = w * 0.5f
        val leftX   = w * 0.25f
        val rightX  = w * 0.75f

        drawCell(canvas, 0f,     0f,      midX,   row1Top, "Hi-Hat",      0, 0)
        drawCell(canvas, midX,   0f,      w,      row1Top, "Crash",        0, 1)
        drawCell(canvas, 0f,     row1Top, midX,   row2Top, "Tom Hi",       1, 0)
        drawCell(canvas, midX,   row1Top, w,      row2Top, "Ride",         1, 1)
        drawCell(canvas, 0f,     row2Top, leftX,  row3Top, "Tom\nLo",      2, 0)
        drawCell(canvas, leftX,  row2Top, rightX, row3Top, "Snare",        2, 1)
        drawCell(canvas, rightX, row2Top, w,      row3Top, "Tom\nLo",      2, 2)
        drawCell(canvas, 0f,     row3Top, midX,   h,       "Hi-Hat\nOpen", 3, 0)
        drawCell(canvas, midX,   row3Top, w,      h,       "Kick",         3, 1)

        canvas.drawLine(0f,    row1Top, w, row1Top, octaveDividerPaint)
        canvas.drawLine(0f,    row2Top, w, row2Top, octaveDividerPaint)
        canvas.drawLine(0f,    row3Top, w, row3Top, gridLinePaint)
        canvas.drawLine(midX,  0f,      midX, h,   gridLinePaint)
        canvas.drawLine(leftX, row2Top, leftX,  row3Top, gridLinePaint)
        canvas.drawLine(rightX,row2Top, rightX, row3Top, gridLinePaint)
    }

    private fun drawCell(canvas: Canvas, left: Float, top: Float,
                         right: Float, bottom: Float,
                         label: String, row: Int, col: Int) {
        val rect = RectF(left, top, right, bottom)
        drawHighlight(canvas, row, col, rect)
        val cx    = left + (right - left) / 2f
        val cy    = top  + (bottom - top) / 2f
        val lines = label.split("\n")
        val lineH = labelPaint.textSize * 1.2f
        val startY = cy - (lines.size - 1) * lineH / 2f -
                (labelPaint.descent() + labelPaint.ascent()) / 2f
        lines.forEachIndexed { i, line ->
            canvas.drawText(line, cx, startY + i * lineH, labelPaint)
        }
    }

    private fun drawHighlight(canvas: Canvas, row: Int, col: Int, rect: RectF) {
        val alpha = highlights[Pair(row, col)]
        if (alpha != null && alpha > 0) {
            highlightPaint.alpha = alpha
            canvas.drawRect(rect, highlightPaint)
        }
    }

    fun highlightCell(normX: Float, normY: Float) {
        val col = (normX * 12f).toInt().coerceIn(0, 11)
        val row = when {
            normY < 0.33f -> 0
            normY < 0.66f -> 1
            else          -> 2
        }
        flashCell(row, col)
    }

    fun highlightOneShotCell(normX: Float, normY: Float) {
        val col = if (normX < 0.5f) 0 else 1
        val row = when {
            normY < 0.25f -> 0
            normY < 0.50f -> 1
            normY < 0.75f -> 2
            else          -> 3
        }
        flashCell(row, col)
    }

    fun highlightBassCell(normX: Float, normY: Float) {
        val col = if (normX < 0.5f) 0 else 1
        val row = if (normY < 0.5f) 0 else 1
        flashCell(row, col)
    }

    fun highlightDrumCell(normX: Float, normY: Float) {
        val (row, col) = when {
            normY < 0.33f -> Pair(0, if (normX < 0.5f) 0 else 1)
            normY < 0.66f -> Pair(1, if (normX < 0.5f) 0 else 1)
            normY < 0.85f -> Pair(2, when {
                normX < 0.25f -> 0
                normX < 0.75f -> 1
                else          -> 2
            })
            else          -> Pair(3, if (normX < 0.5f) 0 else 1)
        }
        flashCell(row, col)
    }

    private fun flashCell(row: Int, col: Int) {
        val key = Pair(row, col)
        animators[key]?.cancel()
        val animator = ValueAnimator.ofInt(200, 0).apply {
            duration = 400
            addUpdateListener {
                highlights[key] = it.animatedValue as Int
                invalidate()
            }
        }
        animators[key] = animator
        highlights[key] = 200
        animator.start()
    }
}