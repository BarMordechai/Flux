package app.shetef.dsp

import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.sin

/** Remove intervals and join the rest with raised-cosine cross-fades. Mirrors fluency/edit.py. */
object Edit {
    fun merge(cuts: List<Pair<Double, Double>>, minLen: Double = 0.01): List<Pair<Double, Double>> {
        val out = ArrayList<DoubleArray>()
        for ((a, b) in cuts.filter { it.second - it.first >= minLen }.sortedWith(compareBy({ it.first }, { it.second }))) {
            if (out.isNotEmpty() && a <= out.last()[1]) out.last()[1] = maxOf(out.last()[1], b)
            else out.add(doubleArrayOf(a, b))
        }
        return out.map { it[0] to it[1] }
    }

    /** Move a cut point to the quietest spot nearby so joins fall between pitch pulses. */
    private fun quietPoint(x: FloatArray, i: Int, radius: Int): Int {
        val lo = maxOf(0, i - radius)
        val hi = minOf(x.size, i + radius)
        if (hi - lo < 4) return i
        var best = lo
        var bestVal = Double.MAX_VALUE
        for (j in 0 until hi - lo) {
            var acc = 0.0
            for (k in j - 16..j + 15) if (k in 0 until hi - lo) acc += abs(x[lo + k])
            if (acc < bestVal) { bestVal = acc; best = lo + j }
        }
        return best
    }

    class Result(val audio: FloatArray, val joins: List<Double>)

    fun applyCuts(x: FloatArray, sr: Int, cuts: List<Pair<Double, Double>>, xfade: Double = 0.015): Result {
        val nXf = (xfade * sr).toInt()
        val radius = (0.004 * sr).toInt()
        val keep = ArrayList<Pair<Int, Int>>()
        var pos = 0
        for ((a, b) in merge(cuts)) {
            val ia = quietPoint(x, (a * sr).toInt(), radius)
            val ib = quietPoint(x, (b * sr).toInt(), radius)
            if (ia > pos) keep.add(pos to ia)
            pos = maxOf(pos, ib)
        }
        if (pos < x.size) keep.add(pos to x.size)
        if (keep.isEmpty()) return Result(FloatArray(0), emptyList())

        val out = FloatBuffer()
        out.addAll(x, keep[0].first, keep[0].second)
        val joins = ArrayList<Double>()
        for ((s, e) in keep.drop(1)) {
            val segLen = e - s
            val n = minOf(nXf, out.size, segLen)
            val base = out.size - n
            for (j in 0 until n) {
                val fi = if (n == 1) 0.0 else sin(PI / 2 * j / (n - 1)).let { it * it }
                out[base + j] = (out[base + j] * (1 - fi) + x[s + j] * fi).toFloat()
            }
            joins.add((out.size - n / 2.0) / sr)
            out.addAll(x, s + n, e)
        }
        return Result(out.toArray(), joins)
    }
}

/** Growable float array. */
class FloatBuffer(capacity: Int = 1 shl 16) {
    private var data = FloatArray(capacity)
    var size = 0
        private set

    private fun ensure(extra: Int) {
        if (size + extra > data.size) data = data.copyOf(maxOf(data.size * 2, size + extra))
    }

    fun add(v: Float) { ensure(1); data[size++] = v }

    fun addAll(src: FloatArray, from: Int, to: Int) {
        if (to <= from) return
        ensure(to - from)
        System.arraycopy(src, from, data, size, to - from)
        size += to - from
    }

    operator fun get(i: Int) = data[i]
    operator fun set(i: Int, v: Float) { data[i] = v }
    fun toArray(): FloatArray = data.copyOf(size)
}
