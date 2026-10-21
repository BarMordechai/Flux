package app.shetef.dsp

import kotlin.math.max

/** Adaptive energy VAD and run helpers. Mirrors fluency/vad.py (energy backend). */
object Vad {
    fun energy(
        f: Features,
        marginDb: Double = 14.0,
        belowSpeechDb: Double = 28.0,
        floorDb: Double = -60.0,
        hangover: Int = 5,
    ): BooleanArray {
        val noise = percentile(f.energyDb, 10.0)
        val speech = percentile(f.energyDb, 95.0)
        // Breath and strain noise in a block sit ~30 dB under speech and must stay "silence".
        val thr = max(max(noise + marginDb, speech - belowSpeechDb), floorDb)
        val mask = BooleanArray(f.n) { f.energyDb[it] > thr }
        return closeGaps(mask, hangover)
    }

    fun closeGaps(mask: BooleanArray, maxGap: Int): BooleanArray {
        val out = mask.copyOf()
        val inv = BooleanArray(mask.size) { !mask[it] }
        for ((s, e) in runs(inv)) if (s > 0 && e < mask.size && e - s <= maxGap) for (i in s until e) out[i] = true
        return out
    }

    /** (start, end) frame pairs for each run of true values. */
    fun runs(mask: BooleanArray): List<Pair<Int, Int>> {
        val out = ArrayList<Pair<Int, Int>>()
        var start = -1
        for (i in mask.indices) {
            if (mask[i] && start < 0) start = i
            if (!mask[i] && start >= 0) { out.add(start to i); start = -1 }
        }
        if (start >= 0) out.add(start to mask.size)
        return out
    }
}
