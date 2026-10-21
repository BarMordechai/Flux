package app.shetef.dsp

/** End-to-end on-device smoothing: audio in, smoothed audio + events out. */
object Pipeline {
    class Result(val audio: FloatArray, val sr: Int, val events: List<Event>) {
        fun count(kind: Kind) = events.count { it.kind == kind }
    }

    fun process(x: FloatArray, sr: Int, mode: Mode = Mode.GENTLE, cfg: DetectConfig = DetectConfig(mode = mode)): Result {
        val peak = x.maxOfOrNull { kotlin.math.abs(it) } ?: 0f
        if (peak < 1e-4f) return Result(x, sr, emptyList())
        val f = Features.compute(x, sr)
        val mask = Vad.energy(f)
        val events = Detect.detect(f, mask, cfg.copy(mode = mode))
        val edited = Edit.applyCuts(x, sr, events.map { it.cutStart to it.cutEnd })
        return Result(edited.audio, sr, events)
    }
}
