# Hebrew word-guided editing (FLEURS he_il + inserted stutters)

80 utterances, 2 stutters inserted in each. Model: CTC wav2vec2 Hebrew.

| mode | word_rep removed | sound_rep removed | prolongation removed | block removed | real speech cut (stuttered input) | utterances with >50 ms real speech cut | real speech cut (fluent input) |
|---|---|---|---|---|---|---|---|
| gentle | 10% | 10% | 59% | 46% | 14.03s total | 19% | 13.03s total |
| full | 22% | 12% | 68% | 54% | 21.59s total | 36% | 19.98s total |
| strong | 23% | 14% | 75% | 74% | 24.06s total | 40% | 22.14s total |

## Examples (examples/NN-before.ogg / NN-after.ogg, full mode)

**01** inserted [('sound_rep', 'מיגרמניה'), ('sound_rep', 'הברי')], real speech cut 0.000s
- text: "הנמל היה האתר של סכסוך  ימי מפורסם מ-1889 כאשר שבע אוניות מגרמניה, ארה""ב ובריטניה סירבו לצאת את הנמל."
- heard: האנמן היה ט של סכוך ימיםמפוסם באל [UNK][UNK]ו נותש כאשור שב אוניות ממגרמניה צות התברית פיברטני סוןלצתאתנמל
- edits: block 6.49-6.93 (breath/strain noise, next to another stutter event)

**02** inserted [('word_rep', 'תקופה'), ('block', 'קבדנית')], real speech cut 0.000s
- text: בזמן תקופה זו בהיסטוריה האירופאית, הכנסייה הקתולית, שהפכה לעשירה ורבת כוח, ספגה ביקורת קפדנית.
- heard: בזמן תקופת תקופה זו בהיסטורירופית הכנסייה טורית שהפכה לשירה ברבת כוח ספגה ביקורת סקבדנית
- edits: block 6.45-7.34 (breath/strain noise)

**03** inserted [('sound_rep', 'לעבראתרים'), ('block', 'ברופאא')], real speech cut 0.000s
- text: רולנדו מנדוזה ירה ברובה ה-M16 שלו אל עבר התיירים.
- heard: שלא אל ללעבר אתירים הם שש ששרונלבמנדוז ירב ברופאא
- edits: block 4.34-5.21 (breath/strain noise)

**04** inserted [('sound_rep', 'בחומ'), ('prolongation', 'טיול')], real speech cut 0.000s
- text: מומלץ בחום למטיילים לשים לב לסכנה של מזג אוויר קשה שפוקד את האזור מכיוון שהוא עלול לפגוע בתכניות הטיול.
- heard: ומנתיינים נסים ללסקנה ש קשה שפוקד את האזורי כיוון שועלול לפגוע בתוכל
- edits: block 2.88-3.3 (breath/strain noise, cut-off sound before the gap); block 3.35-3.83 (breath/strain noise, cut-off sound before the gap); block 3.84-4.28 (breath/strain noise, cut-off sound before the gap); block 4.32-4.8 (breath/strain noise, cut-off sound before the gap); block 5.03-5.34 (breath/strain noise, cut-off sound before the gap, next to another stutter event); block 5.58-5.83 (breath/strain noise, cut-off sound before the gap, next to another stutter event)

**05** inserted [('block', 'משותו'), ('word_rep', 'טיון')], real speech cut 0.210s
- text: שיתוף של טיול וירטואלי משותף הוא גם דרך נהדרת להתבונן בטיול ולשתף כיתות עתידיות בחוויות.
- heard: שיתוף של טיול לטואלים מישותו אוגם דר נדרונין טיון קיו גליש קיות עידיות בחוויות
- edits: prolongation 2.16-2.54 (held 'ל' in 'לטואלים'); block 8.81-9.33 (breath/strain noise, cut-off sound before the gap); block 9.72-10.07 (breath/strain noise, next to another stutter event); block 10.8-11.3 (breath/strain noise)

**06** inserted [('prolongation', 'לפני')], real speech cut 0.050s
- text: בין השעות 22:00-23:00 לפי אזור זמן ההרים (MDT), הוצתה שריפה על ידי האסירים בחצר.
- heard: מבתחצ זה לפני סו שהו
- edits: prolongation 1.7-2.48 (held 'ל' in 'לפני')

**07** inserted [('prolongation', 'מצב'), ('prolongation', 'שוטיתוברחובות')], real speech cut 0.000s
- text: "בישקק תוארה כמתדרדרת למצב של ""אנרכיה"" על ידי משקיף אחד, כשכנופיות שוטטו ברחובות ובזזו חנויות של מוצרי צריכה."
- heard: פישקקתורק כמתרדרת למצ של אנחיה על ידי משקיף אחד כשכנופיות ששותיתו בחובות ויבזיזו חנויות ש מות סר צריה
- edits: 

**08** inserted [('sound_rep', 'היתהיך'), ('sound_rep', 'זמןלגשזמןקצר')], real speech cut 2.300s
- text: הפסקת שינה היא תהליך של יקיצה מכוונת במהלך זמן השינה הרגיל שלך והירדמות זמן קצר לאחר מכן (10–60 דקות).
- heard: הפסקות שהליך שלקיצהלך זזמןלגשזמןקצר לאעשר [UNK]י[UNK]ים דקות
- edits: prolongation 2.82-3.7 (held 'ה' in 'שלקיצהלך'); prolongation 4.66-5.22 (held 'ל' in 'זזמןלגשזמןקצר'); prolongation 5.4-6.2 (held 'ש' in 'זזמןלגשזמןקצר'); prolongation 6.84-7.58 (held 'א' in 'לאעשר')
