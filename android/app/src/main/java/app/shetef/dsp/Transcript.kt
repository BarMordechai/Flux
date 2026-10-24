package app.shetef.dsp

/** Word-guided editing from a verbatim CTC transcript. Mirrors fluency/ctc.py and the transcript parts of detect.py. */
data class Word(val text: String, val start: Double, val end: Double, val chars: List<Triple<String, Double, Double>> = emptyList())

object Transcript {
    const val FRAME = 0.02 // seconds per wav2vec2 output frame

    /** Greedy CTC decode of [frames x vocab] logits into words with character times. */
    fun decodeWords(logits: Array<FloatArray>, vocab: List<String>, blank: Int, delimiter: String = "|"): List<Word> {
        val words = ArrayList<Word>()
        val chars = ArrayList<Triple<String, Int, Int>>()
        fun flush() {
            if (chars.isEmpty()) return
            val spans = chars.map { (c, a, b) -> Triple(c, a * FRAME, (b + 1) * FRAME) }
            words.add(Word(chars.joinToString("") { it.first }, spans.first().second, spans.last().third, spans))
            chars.clear()
        }
        var prev = -1
        for (t in logits.indices) {
            val row = logits[t]
            var id = 0
            for (k in 1 until row.size) if (row[k] > row[id]) id = k
            if (id == prev) {
                if (id != blank && vocab[id] != delimiter && chars.isNotEmpty()) {
                    val last = chars.last()
                    chars[chars.size - 1] = Triple(last.first, last.second, t) // character held over frames
                }
                continue
            }
            prev = id
            if (id == blank) continue
            val tok = vocab[id]
            if (tok == delimiter || tok.isBlank()) flush() else if (!tok.startsWith("<")) chars.add(Triple(tok, t, t))
        }
        flush()
        return words
    }

    private val niqqud = Regex("[֑-ׇ]")
    private val punct = Regex("[^\\p{L}\\p{N}_]")
    fun norm(w: String) = punct.replace(niqqud.replace(w, ""), "").lowercase()

    val allowedDoubles = setOf("לאט", "מאוד", "כן", "לא", "עוד", "יותר", "very", "no", "yes", "bye", "ביי")

    /** Word, part-word and phrase repetitions; cut runs from the first copy to the start of the kept word. */
    fun repetitions(words: List<Word>, mode: Mode): List<Event> {
        val w = words.map { norm(it.text) }
        val links = HashMap<Int, Int>()
        for (i in 0 until words.size - 1) {
            if (w[i].isEmpty()) continue
            val fragment = words[i].text.trimEnd().endsWith("-") || w[i].length == 1
            if (fragment && w[i + 1].startsWith(w[i]) && w[i] != w[i + 1]) {
                links[i] = i + 1
            } else if (w[i] == w[i + 1] && w[i] !in allowedDoubles) {
                links[i] = i + 1
            } else {
                for (n in intArrayOf(3, 2)) {
                    if (i + 2 * n <= w.size && w.subList(i, i + n) == w.subList(i + n, i + 2 * n) &&
                        w.subList(i, i + n).all { it.isNotEmpty() }
                    ) {
                        links[i] = i + n
                        break
                    }
                }
            }
        }
        val events = ArrayList<Event>()
        val seen = HashSet<Int>()
        for (i in links.keys.sorted()) {
            if (i in seen) continue
            val chain = arrayListOf(i)
            while (true) {
                val nxt = links[chain.last()] ?: break
                if (nxt !in links || nxt in seen) break
                chain.add(nxt)
            }
            seen.addAll(chain)
            val target = links[chain.last()]!!
            val cutTo = if (mode.keepOneRepetition) {
                if (chain.size < 2) continue
                words[chain.last()].start
            } else words[target].start
            val a = words[chain.first()].start
            val text = words.subList(chain.first(), target + 1).joinToString(" ") { it.text }
            events.add(Event(Kind.REPETITION, a, words[target].start, a, cutTo, text))
        }
        return events
    }

    /** Held sounds: a long stretch of continuous speech with no new character, before or inside a word. */
    fun prolongations(words: List<Word>, f: Features, mask: BooleanArray, mode: Mode): List<Event> {
        val events = ArrayList<Event>()
        var prevEnd = 0.0
        for (w in words) {
            val spans = w.chars
            val stretches = ArrayList<Triple<Double, Double, String>>()
            if (spans.isNotEmpty()) {
                // Before the first character: from where the current stretch of continuous speech began.
                val fb = minOf(f.frame(spans[0].second), mask.size)
                var fa = fb
                while (fa > 0 && mask[fa - 1]) fa--
                stretches.add(Triple(maxOf(prevEnd, f.t(fa)), spans[0].second, w.text.take(1)))
            }
            for (k in 0 until spans.size - 1) stretches.add(Triple(spans[k].third, spans[k + 1].second, spans[k].first))
            for ((a, b, ch) in stretches) {
                val fa = f.frame(a)
                val fb = f.frame(b)
                if (b - a < mode.prolongMin + 0.1 || fb <= fa) continue
                if ((fa until minOf(fb, mask.size)).any { !mask[it] }) continue // a pause, not a held sound
                val k = mode.prolongKeep / 2
                events.add(Event(Kind.PROLONGATION, a, b, a + 0.05 + k, b - k, "held '$ch' in '${w.text}'"))
            }
            prevEnd = w.end
        }
        return events
    }

    /** Time of the quietest frame in [t+lo, t+hi]: moves a word-based cut point into the dip between sounds. */
    fun snapDown(f: Features, t: Double, lo: Double, hi: Double): Double {
        val a = maxOf(0, f.frame(t + lo))
        val b = minOf(f.n, f.frame(t + hi) + 1)
        if (b <= a) return t
        var min = f.energyDb[a]
        for (i in a until b) min = minOf(min, f.energyDb[i])
        var best = a
        for (i in a until b) if (f.energyDb[i] <= min + 3.0) best = i // the quiet frame nearest the word
        return f.t(best)
    }
}
