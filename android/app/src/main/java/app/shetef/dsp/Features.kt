package app.shetef.dsp

import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.floor
import kotlin.math.log10
import kotlin.math.max
import kotlin.math.min
import kotlin.math.pow
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlin.math.sqrt

/** Frame-level features on a 25 ms window / 10 ms hop grid. Mirrors fluency/features.py. */
class Features(val sr: Int, val hop: Int, val energyDb: DoubleArray, val logmel: Array<DoubleArray>) {
    val n: Int get() = energyDb.size
    fun t(frame: Int): Double = frame.toDouble() * hop / sr
    fun frame(seconds: Double): Int = (seconds * sr / hop).roundToInt()

    companion object {
        const val N_MELS = 40

        fun compute(x: FloatArray, sr: Int): Features {
            val win = (0.025 * sr).toInt()
            val hop = (0.010 * sr).toInt()
            var nFft = 1
            while (nFft < win) nFft = nFft shl 1
            val padLen = x.size + 2 * (win / 2)
            val n = max(1, 1 + (padLen - win) / hop)
            val hann = DoubleArray(win) { 0.5 - 0.5 * cos(2 * PI * it / (win - 1)) }
            val fb = melFilterbank(sr, nFft)
            val energy = DoubleArray(n)
            val logmel = Array(n) { DoubleArray(N_MELS) }
            val re = DoubleArray(nFft)
            val im = DoubleArray(nFft)
            val power = DoubleArray(nFft / 2 + 1)
            for (f in 0 until n) {
                var sum = 0.0
                re.fill(0.0); im.fill(0.0)
                for (j in 0 until win) {
                    val i = f * hop + j - win / 2
                    val v = if (i in x.indices) x[i].toDouble() else 0.0
                    sum += v * v
                    re[j] = v * hann[j]
                }
                energy[f] = 20 * log10(sqrt(sum / win + 1e-12) + 1e-9)
                Fft.transform(re, im)
                for (k in power.indices) power[k] = re[k] * re[k] + im[k] * im[k]
                for (m in 0 until N_MELS) {
                    var acc = 0.0
                    val row = fb[m]
                    for (k in power.indices) if (row[k] != 0.0) acc += row[k] * power[k]
                    logmel[f][m] = 10 * log10(acc + 1e-10)
                }
            }
            return Features(sr, hop, energy, logmel)
        }

        private fun mel(f: Double) = 2595.0 * log10(1.0 + f / 700.0)
        private fun melInv(m: Double) = 700.0 * (10.0.pow(m / 2595.0) - 1.0)

        fun melFilterbank(sr: Int, nFft: Int, nMels: Int = N_MELS, fmin: Double = 60.0): Array<DoubleArray> {
            val fmax = sr / 2.0 - 400
            val lo = mel(fmin)
            val hi = mel(fmax)
            val pts = DoubleArray(nMels + 2) { melInv(lo + (hi - lo) * it / (nMels + 1)) }
            val nBins = nFft / 2 + 1
            return Array(nMels) { i ->
                DoubleArray(nBins) { k ->
                    val b = k.toDouble() * sr / nFft
                    val up = (b - pts[i]) / (pts[i + 1] - pts[i])
                    val down = (pts[i + 2] - b) / (pts[i + 2] - pts[i + 1])
                    max(0.0, min(up, down))
                }
            }
        }
    }

    /** Mean |dB| difference between the average spectrum just before and just after each frame. */
    fun spectralChange(half: Int = 5): DoubleArray {
        val m = N_MELS
        val c = Array(n + 1) { DoubleArray(m) }
        for (t in 0 until n) for (k in 0 until m) c[t + 1][k] = c[t][k] + logmel[t][k]
        val out = DoubleArray(n) { Double.POSITIVE_INFINITY }
        for (t in half until n - half) {
            var acc = 0.0
            for (k in 0 until m) {
                val before = (c[t][k] - c[t - half][k]) / half
                val after = (c[t + half][k] - c[t][k]) / half
                acc += abs(after - before)
            }
            out[t] = acc / m
        }
        return out
    }
}

/** In-place iterative radix-2 complex FFT. */
object Fft {
    fun transform(re: DoubleArray, im: DoubleArray) {
        val n = re.size
        var j = 0
        for (i in 1 until n) {
            var bit = n shr 1
            while (j and bit != 0) { j = j xor bit; bit = bit shr 1 }
            j = j xor bit
            if (i < j) {
                var t = re[i]; re[i] = re[j]; re[j] = t
                t = im[i]; im[i] = im[j]; im[j] = t
            }
        }
        var len = 2
        while (len <= n) {
            val ang = -2 * PI / len
            val wr = cos(ang)
            val wi = sin(ang)
            var i = 0
            while (i < n) {
                var cr = 1.0
                var ci = 0.0
                for (k in 0 until len / 2) {
                    val a = i + k
                    val b = a + len / 2
                    val xr = re[b] * cr - im[b] * ci
                    val xi = re[b] * ci + im[b] * cr
                    re[b] = re[a] - xr; im[b] = im[a] - xi
                    re[a] += xr; im[a] += xi
                    val nr = cr * wr - ci * wi
                    ci = cr * wi + ci * wr
                    cr = nr
                }
                i += len
            }
            len = len shl 1
        }
    }
}

/** numpy.percentile with linear interpolation. */
fun percentile(a: DoubleArray, q: Double): Double {
    if (a.isEmpty()) return 0.0
    val s = a.sortedArray()
    val idx = q / 100.0 * (s.size - 1)
    val lo = floor(idx).toInt()
    val hi = min(lo + 1, s.size - 1)
    return s[lo] + (idx - lo) * (s[hi] - s[lo])
}
