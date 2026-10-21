# SEP-28k calibration

40 episodes, 2799 clips, 537 fluent clips.
Positives: Prolongation 254, Block 297, SoundRep 268, WordRep 375, Interjection 735

## Current modes

| mode | FP on fluent clips | any stutter | Prolongation | Block | SoundRep | WordRep |
|---|---|---|---|---|---|---|
| gentle | 0.330 | 0.468 | 0.020 | 0.576 | 0.034 | 0.008 |
| full | 0.443 | 0.604 | 0.098 | 0.667 | 0.257 | 0.123 |
| strong | 0.598 | 0.788 | 0.409 | 0.771 | 0.429 | 0.317 |

## prolongation

Current (full mode): {'steady_db': 2.2, 'prolong_min': 0.3}

| FP rate on fluent clips | recall | Prolongation | params |
|---|---|---|---|
| 0.000 | 0.016 | 0.016 | {'prolong_min': 0.3, 'steady_db': 1.6} |
| 0.000 | 0.020 | 0.020 | {'prolong_min': 0.45, 'steady_db': 2.2} |
| 0.002 | 0.031 | 0.031 | {'prolong_min': 0.22, 'steady_db': 1.6} |
| 0.004 | 0.098 | 0.098 | {'prolong_min': 0.3, 'steady_db': 2.2} |
| 0.007 | 0.209 | 0.209 | {'prolong_min': 0.3, 'steady_db': 2.8} |
| 0.015 | 0.224 | 0.224 | {'prolong_min': 0.22, 'steady_db': 2.2} |
| 0.020 | 0.283 | 0.283 | {'prolong_min': 0.3, 'steady_db': 3.4} |
| 0.035 | 0.382 | 0.382 | {'prolong_min': 0.3, 'steady_db': 4.0} |
| 0.047 | 0.409 | 0.409 | {'prolong_min': 0.22, 'steady_db': 2.8} |
| 0.101 | 0.508 | 0.508 | {'prolong_min': 0.22, 'steady_db': 3.4} |
| 0.102 | 0.543 | 0.543 | {'prolong_min': 0.18, 'steady_db': 2.8} |
| 0.155 | 0.575 | 0.575 | {'prolong_min': 0.22, 'steady_db': 4.0} |
| 0.203 | 0.673 | 0.673 | {'prolong_min': 0.18, 'steady_db': 3.4} |
| 0.335 | 0.787 | 0.787 | {'prolong_min': 0.18, 'steady_db': 4.0} |

## repetition

Current (full mode): {'fragment_sim_db': 4.0, 'fragment_max': 0.35, 'fragment_gap_max': 0.6}

| FP rate on fluent clips | recall | SoundRep | WordRep | params |
|---|---|---|---|---|
| 0.004 | 0.089 | 0.127 | 0.051 | {'fragment_gap_max': 0.4, 'fragment_max': 0.25, 'fragment_sim_db': 3.0} |
| 0.006 | 0.093 | 0.131 | 0.056 | {'fragment_gap_max': 0.6, 'fragment_max': 0.25, 'fragment_sim_db': 3.0} |
| 0.007 | 0.095 | 0.134 | 0.056 | {'fragment_gap_max': 0.8, 'fragment_max': 0.25, 'fragment_sim_db': 3.0} |
| 0.011 | 0.102 | 0.146 | 0.059 | {'fragment_gap_max': 0.4, 'fragment_max': 0.35, 'fragment_sim_db': 3.0} |
| 0.013 | 0.110 | 0.153 | 0.067 | {'fragment_gap_max': 0.6, 'fragment_max': 0.35, 'fragment_sim_db': 3.0} |
| 0.015 | 0.112 | 0.157 | 0.067 | {'fragment_gap_max': 0.8, 'fragment_max': 0.35, 'fragment_sim_db': 3.0} |
| 0.015 | 0.116 | 0.160 | 0.072 | {'fragment_gap_max': 1.0, 'fragment_max': 0.35, 'fragment_sim_db': 3.0} |
| 0.019 | 0.159 | 0.224 | 0.093 | {'fragment_gap_max': 0.4, 'fragment_max': 0.25, 'fragment_sim_db': 4.0} |
| 0.022 | 0.164 | 0.231 | 0.096 | {'fragment_gap_max': 0.6, 'fragment_max': 0.25, 'fragment_sim_db': 4.0} |
| 0.024 | 0.167 | 0.235 | 0.099 | {'fragment_gap_max': 0.8, 'fragment_max': 0.25, 'fragment_sim_db': 4.0} |
| 0.024 | 0.172 | 0.243 | 0.101 | {'fragment_gap_max': 1.0, 'fragment_max': 0.25, 'fragment_sim_db': 4.0} |
| 0.034 | 0.184 | 0.250 | 0.117 | {'fragment_gap_max': 0.4, 'fragment_max': 0.35, 'fragment_sim_db': 4.0} |
| 0.037 | 0.190 | 0.257 | 0.123 | {'fragment_gap_max': 0.6, 'fragment_max': 0.35, 'fragment_sim_db': 4.0} |
| 0.041 | 0.193 | 0.261 | 0.125 | {'fragment_gap_max': 0.8, 'fragment_max': 0.35, 'fragment_sim_db': 4.0} |
| 0.045 | 0.204 | 0.272 | 0.136 | {'fragment_gap_max': 1.0, 'fragment_max': 0.35, 'fragment_sim_db': 4.0} |
| 0.056 | 0.212 | 0.272 | 0.152 | {'fragment_gap_max': 0.4, 'fragment_max': 0.45, 'fragment_sim_db': 4.0} |
| 0.063 | 0.219 | 0.280 | 0.157 | {'fragment_gap_max': 0.6, 'fragment_max': 0.45, 'fragment_sim_db': 4.0} |
| 0.069 | 0.226 | 0.287 | 0.165 | {'fragment_gap_max': 0.8, 'fragment_max': 0.45, 'fragment_sim_db': 4.0} |
| 0.074 | 0.257 | 0.336 | 0.179 | {'fragment_gap_max': 0.4, 'fragment_max': 0.25, 'fragment_sim_db': 5.5} |
| 0.091 | 0.274 | 0.358 | 0.189 | {'fragment_gap_max': 0.6, 'fragment_max': 0.25, 'fragment_sim_db': 5.5} |
| 0.101 | 0.282 | 0.369 | 0.195 | {'fragment_gap_max': 0.8, 'fragment_max': 0.25, 'fragment_sim_db': 5.5} |
| 0.104 | 0.293 | 0.384 | 0.203 | {'fragment_gap_max': 1.0, 'fragment_max': 0.25, 'fragment_sim_db': 5.5} |
| 0.117 | 0.305 | 0.373 | 0.237 | {'fragment_gap_max': 0.4, 'fragment_max': 0.35, 'fragment_sim_db': 5.5} |
| 0.136 | 0.321 | 0.392 | 0.251 | {'fragment_gap_max': 0.6, 'fragment_max': 0.35, 'fragment_sim_db': 5.5} |
| 0.147 | 0.331 | 0.403 | 0.259 | {'fragment_gap_max': 0.8, 'fragment_max': 0.35, 'fragment_sim_db': 5.5} |
| 0.155 | 0.351 | 0.425 | 0.277 | {'fragment_gap_max': 1.0, 'fragment_max': 0.35, 'fragment_sim_db': 5.5} |
| 0.175 | 0.359 | 0.451 | 0.267 | {'fragment_gap_max': 0.8, 'fragment_max': 0.25, 'fragment_sim_db': 7.0} |
| 0.182 | 0.374 | 0.474 | 0.275 | {'fragment_gap_max': 1.0, 'fragment_max': 0.25, 'fragment_sim_db': 7.0} |
| 0.201 | 0.379 | 0.440 | 0.317 | {'fragment_gap_max': 0.4, 'fragment_max': 0.35, 'fragment_sim_db': 7.0} |
| 0.203 | 0.389 | 0.429 | 0.349 | {'fragment_gap_max': 0.4, 'fragment_max': 0.6, 'fragment_sim_db': 5.5} |
| 0.212 | 0.398 | 0.455 | 0.341 | {'fragment_gap_max': 1.0, 'fragment_max': 0.45, 'fragment_sim_db': 5.5} |
| 0.220 | 0.414 | 0.455 | 0.373 | {'fragment_gap_max': 0.6, 'fragment_max': 0.6, 'fragment_sim_db': 5.5} |
| 0.240 | 0.420 | 0.493 | 0.347 | {'fragment_gap_max': 0.8, 'fragment_max': 0.35, 'fragment_sim_db': 7.0} |
| 0.253 | 0.431 | 0.470 | 0.392 | {'fragment_gap_max': 0.8, 'fragment_max': 0.6, 'fragment_sim_db': 5.5} |
| 0.253 | 0.445 | 0.522 | 0.368 | {'fragment_gap_max': 1.0, 'fragment_max': 0.35, 'fragment_sim_db': 7.0} |
| 0.266 | 0.454 | 0.493 | 0.416 | {'fragment_gap_max': 1.0, 'fragment_max': 0.6, 'fragment_sim_db': 5.5} |
| 0.304 | 0.473 | 0.534 | 0.413 | {'fragment_gap_max': 0.8, 'fragment_max': 0.45, 'fragment_sim_db': 7.0} |
| 0.309 | 0.486 | 0.519 | 0.453 | {'fragment_gap_max': 0.4, 'fragment_max': 0.6, 'fragment_sim_db': 7.0} |
| 0.320 | 0.504 | 0.567 | 0.440 | {'fragment_gap_max': 1.0, 'fragment_max': 0.45, 'fragment_sim_db': 7.0} |
| 0.330 | 0.523 | 0.563 | 0.483 | {'fragment_gap_max': 0.6, 'fragment_max': 0.6, 'fragment_sim_db': 7.0} |
| 0.371 | 0.548 | 0.590 | 0.507 | {'fragment_gap_max': 0.8, 'fragment_max': 0.6, 'fragment_sim_db': 7.0} |
| 0.393 | 0.579 | 0.619 | 0.539 | {'fragment_gap_max': 1.0, 'fragment_max': 0.6, 'fragment_sim_db': 7.0} |

## word_repetition

Current (full mode): {'word_dtw_db': 0.0, 'word_max': 0.8, 'word_gap_max': 0.5}

| FP rate on fluent clips | recall | WordRep | SoundRep | params |
|---|---|---|---|---|
| 0.002 | 0.019 | 0.027 | 0.011 | {'word_dtw_db': 2.0, 'word_gap_max': 0.3, 'word_max': 0.5} |
| 0.002 | 0.023 | 0.027 | 0.019 | {'word_dtw_db': 2.0, 'word_gap_max': 0.5, 'word_max': 0.5} |
| 0.002 | 0.026 | 0.029 | 0.022 | {'word_dtw_db': 2.0, 'word_gap_max': 0.8, 'word_max': 0.5} |
| 0.004 | 0.064 | 0.053 | 0.075 | {'word_dtw_db': 2.5, 'word_gap_max': 0.3, 'word_max': 0.5} |
| 0.006 | 0.081 | 0.064 | 0.097 | {'word_dtw_db': 2.5, 'word_gap_max': 0.5, 'word_max': 0.5} |
| 0.006 | 0.083 | 0.069 | 0.097 | {'word_dtw_db': 2.5, 'word_gap_max': 0.5, 'word_max': 0.8} |
| 0.007 | 0.087 | 0.067 | 0.108 | {'word_dtw_db': 2.5, 'word_gap_max': 0.8, 'word_max': 0.5} |
| 0.007 | 0.090 | 0.072 | 0.108 | {'word_dtw_db': 2.5, 'word_gap_max': 0.8, 'word_max': 0.8} |
| 0.011 | 0.129 | 0.101 | 0.157 | {'word_dtw_db': 3.0, 'word_gap_max': 0.3, 'word_max': 0.5} |
| 0.011 | 0.138 | 0.115 | 0.160 | {'word_dtw_db': 3.0, 'word_gap_max': 0.3, 'word_max': 0.8} |
| 0.017 | 0.150 | 0.120 | 0.179 | {'word_dtw_db': 3.0, 'word_gap_max': 0.5, 'word_max': 0.5} |
| 0.017 | 0.162 | 0.141 | 0.183 | {'word_dtw_db': 3.0, 'word_gap_max': 0.5, 'word_max': 0.8} |
| 0.020 | 0.170 | 0.139 | 0.201 | {'word_dtw_db': 3.0, 'word_gap_max': 0.8, 'word_max': 0.5} |
| 0.020 | 0.183 | 0.160 | 0.205 | {'word_dtw_db': 3.0, 'word_gap_max': 0.8, 'word_max': 0.8} |
| 0.034 | 0.188 | 0.187 | 0.190 | {'word_dtw_db': 3.5, 'word_gap_max': 0.3, 'word_max': 0.8} |
| 0.037 | 0.191 | 0.181 | 0.201 | {'word_dtw_db': 3.5, 'word_gap_max': 0.5, 'word_max': 0.5} |
| 0.043 | 0.215 | 0.221 | 0.209 | {'word_dtw_db': 3.5, 'word_gap_max': 0.5, 'word_max': 0.8} |
| 0.052 | 0.238 | 0.245 | 0.231 | {'word_dtw_db': 3.5, 'word_gap_max': 0.8, 'word_max': 0.8} |
| 0.095 | 0.255 | 0.248 | 0.261 | {'word_dtw_db': 4.0, 'word_gap_max': 0.5, 'word_max': 0.5} |
| 0.095 | 0.258 | 0.261 | 0.254 | {'word_dtw_db': 4.0, 'word_gap_max': 0.3, 'word_max': 0.8} |
| 0.108 | 0.279 | 0.277 | 0.280 | {'word_dtw_db': 4.0, 'word_gap_max': 0.8, 'word_max': 0.5} |
| 0.110 | 0.286 | 0.296 | 0.276 | {'word_dtw_db': 4.0, 'word_gap_max': 0.5, 'word_max': 0.8} |
| 0.128 | 0.315 | 0.331 | 0.299 | {'word_dtw_db': 4.0, 'word_gap_max': 0.8, 'word_max': 0.8} |
| 0.166 | 0.322 | 0.323 | 0.321 | {'word_dtw_db': 4.5, 'word_gap_max': 0.5, 'word_max': 0.5} |
| 0.190 | 0.338 | 0.347 | 0.328 | {'word_dtw_db': 4.5, 'word_gap_max': 0.3, 'word_max': 0.8} |
| 0.194 | 0.354 | 0.357 | 0.351 | {'word_dtw_db': 4.5, 'word_gap_max': 0.8, 'word_max': 0.5} |
| 0.210 | 0.380 | 0.397 | 0.362 | {'word_dtw_db': 4.5, 'word_gap_max': 0.5, 'word_max': 0.8} |
| 0.246 | 0.386 | 0.365 | 0.407 | {'word_dtw_db': 5.0, 'word_gap_max': 0.5, 'word_max': 0.5} |
| 0.248 | 0.418 | 0.440 | 0.396 | {'word_dtw_db': 4.5, 'word_gap_max': 0.8, 'word_max': 0.8} |
| 0.287 | 0.426 | 0.408 | 0.444 | {'word_dtw_db': 5.0, 'word_gap_max': 0.8, 'word_max': 0.5} |
| 0.311 | 0.465 | 0.464 | 0.466 | {'word_dtw_db': 5.0, 'word_gap_max': 0.5, 'word_max': 0.8} |
| 0.369 | 0.514 | 0.517 | 0.511 | {'word_dtw_db': 5.0, 'word_gap_max': 0.8, 'word_max': 0.8} |

## block

Current (full mode): {'block_min': 0.25, 'strain_margin_db': 6.0}

| FP rate on fluent clips | recall | Block | params |
|---|---|---|---|
| 0.298 | 0.535 | 0.535 | {'block_min': 0.35, 'strain_margin_db': 8.0} |
| 0.343 | 0.589 | 0.589 | {'block_min': 0.35, 'strain_margin_db': 6.0} |
| 0.374 | 0.606 | 0.606 | {'block_min': 0.25, 'strain_margin_db': 8.0} |
| 0.378 | 0.616 | 0.616 | {'block_min': 0.35, 'strain_margin_db': 4.5} |
| 0.412 | 0.650 | 0.650 | {'block_min': 0.18, 'strain_margin_db': 8.0} |
| 0.432 | 0.667 | 0.667 | {'block_min': 0.25, 'strain_margin_db': 6.0} |
| 0.466 | 0.724 | 0.724 | {'block_min': 0.18, 'strain_margin_db': 6.0} |
| 0.497 | 0.727 | 0.727 | {'block_min': 0.12, 'strain_margin_db': 8.0} |
| 0.503 | 0.761 | 0.761 | {'block_min': 0.18, 'strain_margin_db': 4.5} |
| 0.546 | 0.801 | 0.801 | {'block_min': 0.12, 'strain_margin_db': 6.0} |
| 0.594 | 0.832 | 0.832 | {'block_min': 0.12, 'strain_margin_db': 4.5} |
| 0.670 | 0.875 | 0.875 | {'block_min': 0.12, 'strain_margin_db': 3.0} |
