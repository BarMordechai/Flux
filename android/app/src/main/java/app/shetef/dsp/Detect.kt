package app.shetef.dsp

import kotlin.math.abs

/** Acoustic stutter detection: repetitions, prolongations, blocks. Mirrors fluency/detect.py. */
// Calibrated on SEP-28k (tools/calibrate_sep28k.py); keep in sync with MODES in fluency/detect.py.
enum class Mode(
    val prolongMin: Double,
    val prolongKeep: Double,
    val blockMin: Double,
    val blockKeep: Double,
    val pauseMax: Double,
    val pauseKeep: Double,
    val keepOneRepetition: Boolean,
    val fragmentMax: Double,
    val fragmentGapMax: Double,
    val fragmentSimDb: Double,
    val steadyDb: Double,
    val wordDtwDb: Double,
    val wordMax: Double,
    val wordGapMax: Double,
) {
    GENTLE(0.30, 0.20, 0.35, 0.25, 1.6, 0.9, true, 0.35, 0.6, 4.0, 2.8, 3.0, 0.8, 0.5),
    FULL(0.22, 0.12, 0.25, 0.12, 1.0, 0.55, false, 0.25, 0.4, 5.5, 2.8, 3.0, 0.8, 0.8),
    // Looser detectors and harder compression: fewer misses, less natural.
    STRONG(0.22, 0.08, 0.18, 0.08, 0.7, 0.4, false, 0.35, 0.6, 5.5, 3.4, 3.5, 0.8, 0.8),
}

enum class Kind { REPETITION, PROLONGATION, BLOCK, PAUSE, EDGE }

data class Event(val kind: Kind, val start: Double, val end: Double, val cutStart: Double, val cutEnd: Double, val note: String)

data class DetectConfig(
    val mode: Mode = Mode.GENTLE,
    val edgeKeep: Double = 0.25,
    val strainMarginDb: Double = 6.0,
    // Acoustic repetition/prolongation detection cannot tell a stutter from a real word reliably (testers heard
    // whole words cut), so by default it only informs block detection and nothing it finds is removed.
    val acousticSpeechCuts: Boolean = false,
    val silenceMargin: Double = 0.08, // never cut closer than this to detected speech (s)
)

object Detect {
    private fun profile(f: Features, a: Int, b: Int): DoubleArray {
        val p = DoubleArray(Features.N_MELS)
        for (t in a until b) for (k in p.indices) p[k] += f.logmel[t][k]
        for (k in p.indices) p[k] /= (b - a)
        val mean = p.average()
        for (k in p.indices) p[k] -= mean
        return p
    }

    private fun chains(n: Int, linked: (Int) -> Boolean): List<List<Int>> {
        val out = ArrayList<List<Int>>()
        var cur = ArrayList<Int>()
        for (i in 0 until n) {
            if (linked(i)) cur.add(i) else if (cur.isNotEmpty()) { out.add(cur); cur = ArrayList() }
        }
        if (cur.isNotEmpty()) out.add(cur)
        return out
    }

    fun acousticRepetitions(f: Features, regions: List<Pair<Int, Int>>, cfg: DetectConfig): List<Event> {
        fun isFragment(i: Int): Boolean {
            if (i + 1 >= regions.size) return false
            val (s, e) = regions[i]
            val (ns, ne) = regions[i + 1]
            if (f.t(e - s) > cfg.mode.fragmentMax || f.t(ns - e) > cfg.mode.fragmentGapMax) return false
            val n = e - s
            if (ne - ns < n) return false
            val p = profile(f, s, e)
            val q = profile(f, ns, ns + n)
            var d = 0.0
            for (k in p.indices) d += abs(p[k] - q[k])
            return d / p.size < cfg.mode.fragmentSimDb
        }

        val events = ArrayList<Event>()
        for (chain in chains(regions.size, ::isFragment)) {
            val first = chain.first()
            val last = chain.last()
            val cutEnd = if (cfg.mode.keepOneRepetition) {
                if (chain.size < 2) continue
                regions[last].first // keep the last fragment
            } else regions[last + 1].first
            val a = f.t(regions[first].first)
            events.add(Event(Kind.REPETITION, a, f.t(regions[last + 1].first), a, f.t(cutEnd), "${chain.size} fragment(s)"))
        }
        return events
    }

    /** Open-end DTW: how well spectral-shape sequence a matches the start of b (mean dB per band). */
    fun dtwDistance(f: Features, aStart: Int, aEnd: Int, bStart: Int, bEnd: Int, minRatio: Double = 0.7): Double {
        val n = aEnd - aStart
        val m = bEnd - bStart
        val bands = Features.N_MELS
        fun shape(t: Int): DoubleArray {
            val row = f.logmel[t]
            val mean = row.average()
            return DoubleArray(bands) { row[it] - mean }
        }
        val a = Array(n) { shape(aStart + it) }
        val b = Array(m) { shape(bStart + it) }
        val inf = Double.POSITIVE_INFINITY
        var prev = DoubleArray(m + 1) { if (it == 0) 0.0 else inf }
        for (i in 1..n) {
            val cur = DoubleArray(m + 1) { inf }
            for (j in 1..m) {
                var c = 0.0
                val ai = a[i - 1]
                val bj = b[j - 1]
                for (k in 0 until bands) c += abs(ai[k] - bj[k])
                cur[j] = c / bands + minOf(prev[j], cur[j - 1], prev[j - 1])
            }
            prev = cur
        }
        var best = inf
        for (j in maxOf(1, (minRatio * n).toInt())..m) best = minOf(best, prev[j] / (n + j))
        return best
    }

    fun wordRepetitions(f: Features, regions: List<Pair<Int, Int>>, cfg: DetectConfig): List<Event> {
        val m = cfg.mode
        if (m.wordDtwDb <= 0) return emptyList()
        fun repeats(i: Int): Boolean {
            if (i + 1 >= regions.size) return false
            val (s, e) = regions[i]
            val (ns, ne) = regions[i + 1]
            val dur = f.t(e - s)
            if (dur < 0.12 || dur > m.wordMax || f.t(ns - e) > m.wordGapMax) return false
            val n = e - s
            if (ne - ns < (0.7 * n).toInt()) return false
            val bEnd = minOf(ne, ns + (1.4 * n).toInt())
            return dtwDistance(f, s, e, ns, bEnd) < m.wordDtwDb
        }

        val events = ArrayList<Event>()
        for (chain in chains(regions.size, ::repeats)) {
            val first = chain.first()
            val last = chain.last()
            val cutEnd = if (m.keepOneRepetition) {
                if (chain.size < 2) continue
                regions[last].first
            } else regions[last + 1].first
            val a = f.t(regions[first].first)
            events.add(Event(Kind.REPETITION, a, f.t(regions[last + 1].first), a, f.t(cutEnd), "${chain.size} word repeat(s)"))
        }
        return events
    }

    fun prolongations(f: Features, mask: BooleanArray, regions: List<Pair<Int, Int>>, cfg: DetectConfig): List<Event> {
        val half = 5
        val change = f.spectralChange(half)
        val steady = BooleanArray(f.n) { change[it] < cfg.mode.steadyDb && mask[it] }
        val events = ArrayList<Event>()
        for ((s0, e0) in Vad.runs(steady)) {
            val s = maxOf(0, s0 - half)
            val e = minOf(f.n, e0 + half)
            val dur = f.t(e - s)
            val regionEnd = regions.firstOrNull { it.first <= s && s < it.second }?.second ?: e
            val phraseFinal = f.t(regionEnd - e) < 0.12
            val need = cfg.mode.prolongMin * (if (phraseFinal) 2.0 else 1.0) // final lengthening is natural
            if (dur < need) continue
            val a = f.t(s)
            val b = f.t(e)
            val k = cfg.mode.prolongKeep / 2
            events.add(Event(Kind.PROLONGATION, a, b, a + k, b - k, "%.2fs steady sound".format(dur)))
        }
        return events
    }

    fun gaps(f: Features, regions: List<Pair<Int, Int>>, events: List<Event>, cfg: DetectConfig, words: List<Word>? = null): List<Event> {
        val out = ArrayList<Event>()
        val noise = percentile(f.energyDb, 10.0)
        val total = f.t(f.n)
        if (regions.isNotEmpty()) {
            val lead = f.t(regions.first().first)
            val trailStart = f.t(regions.last().second)
            if (lead > cfg.edgeKeep) out.add(Event(Kind.EDGE, 0.0, lead, 0.0, lead - cfg.edgeKeep, "leading silence"))
            if (total - trailStart > cfg.edgeKeep)
                out.add(Event(Kind.EDGE, trailStart, total, trailStart + cfg.edgeKeep, total, "trailing silence"))
        }
        val edges = events.flatMap { listOf(it.end, it.start) }
        for (i in 0 until regions.size - 1) {
            val (ps, pe) = regions[i]
            val ns = regions[i + 1].first
            val a = f.t(pe)
            val b = f.t(ns)
            val dur = b - a
            if (dur < cfg.mode.blockMin) continue
            val reasons = ArrayList<String>()
            var loud = 0
            for (t in pe until ns) if (f.energyDb[t] > noise + cfg.strainMarginDb) loud++
            if (loud.toDouble() / (ns - pe) > 0.3) reasons.add("breath/strain noise")
            if (f.t(pe - ps) < 0.15) reasons.add("cut-off sound before the gap")
            if (edges.any { abs(it - a) < 0.1 || abs(it - b) < 0.1 }) reasons.add("next to another stutter event")
            for (wd in words.orEmpty()) {
                if (wd.start < a - 0.05 && wd.end > b + 0.05) { reasons.add("inside the word '${wd.text}'"); break }
                if (abs(wd.end - a) < 0.15 && wd.text.trimEnd().endsWith("-")) { reasons.add("after the fragment '${wd.text}'"); break }
            }
            if (reasons.isNotEmpty()) {
                val k = maxOf(cfg.mode.blockKeep / 2, cfg.silenceMargin)
                out.add(Event(Kind.BLOCK, a, b, a + k, b - k, reasons.joinToString(", ")))
            } else if (dur > cfg.mode.pauseMax) {
                val k = maxOf(cfg.mode.pauseKeep / 2, cfg.silenceMargin)
                out.add(Event(Kind.PAUSE, a, b, a + k, b - k, "long pause shortened"))
            }
        }
        return out
    }

    fun detect(f: Features, mask: BooleanArray, cfg: DetectConfig, words: List<Word>? = null): List<Event> {
        val regions = Vad.runs(mask)
        val events = ArrayList<Event>()
        val acoustic = acousticRepetitions(f, regions, cfg) + wordRepetitions(f, regions, cfg) +
            prolongations(f, mask, regions, cfg)
        if (cfg.acousticSpeechCuts) events += acoustic
        if (words != null) {
            // Grounded in recognised words, so safe to cut. CTC character times are spikes, not onsets:
            // snap each cut edge to the quietest point just before the word it sits on.
            for (e in Transcript.repetitions(words, cfg.mode)) {
                val a = Transcript.snapDown(f, e.cutStart, -0.15, 0.0)
                val b = Transcript.snapDown(f, e.cutEnd, -0.25, -0.01)
                events += e.copy(cutStart = a, cutEnd = maxOf(a, b))
            }
            events += Transcript.prolongations(words, f, mask, cfg.mode)
        }
        events += gaps(f, regions, acoustic + events, cfg, words)
        return events.sortedBy { it.start }
    }
}
