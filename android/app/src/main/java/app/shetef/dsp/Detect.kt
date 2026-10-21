package app.shetef.dsp

import kotlin.math.abs

/** Acoustic stutter detection: repetitions, prolongations, blocks. Mirrors fluency/detect.py. */
enum class Mode(
    val prolongMin: Double,
    val prolongKeep: Double,
    val blockMin: Double,
    val blockKeep: Double,
    val pauseMax: Double,
    val pauseKeep: Double,
    val keepOneRepetition: Boolean,
    val fragmentMax: Double = 0.35,
    val fragmentGapMax: Double = 0.6,
    val fragmentSimDb: Double = 4.0,
    val steadyDb: Double = 2.2,
) {
    GENTLE(0.45, 0.20, 0.35, 0.25, 1.6, 0.9, true),
    FULL(0.30, 0.12, 0.25, 0.12, 1.0, 0.55, false),
    // Looser detectors and harder compression: fewer misses, less natural.
    STRONG(0.22, 0.08, 0.18, 0.08, 0.7, 0.4, false, 0.45, 0.8, 5.5, 2.8),
}

enum class Kind { REPETITION, PROLONGATION, BLOCK, PAUSE, EDGE }

data class Event(val kind: Kind, val start: Double, val end: Double, val cutStart: Double, val cutEnd: Double, val note: String)

data class DetectConfig(
    val mode: Mode = Mode.GENTLE,
    val edgeKeep: Double = 0.25,
    val strainMarginDb: Double = 6.0,
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

    fun gaps(f: Features, regions: List<Pair<Int, Int>>, events: List<Event>, cfg: DetectConfig): List<Event> {
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
            if (reasons.isNotEmpty()) {
                val k = cfg.mode.blockKeep / 2
                out.add(Event(Kind.BLOCK, a, b, a + k, b - k, reasons.joinToString(", ")))
            } else if (dur > cfg.mode.pauseMax) {
                val k = cfg.mode.pauseKeep / 2
                out.add(Event(Kind.PAUSE, a, b, a + k, b - k, "long pause shortened"))
            }
        }
        return out
    }

    fun detect(f: Features, mask: BooleanArray, cfg: DetectConfig): List<Event> {
        val regions = Vad.runs(mask)
        val events = ArrayList<Event>()
        events += acousticRepetitions(f, regions, cfg)
        events += prolongations(f, mask, regions, cfg)
        events += gaps(f, regions, events, cfg)
        return events.sortedBy { it.start }
    }
}
