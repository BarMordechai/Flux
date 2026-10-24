# Hebrew word-guided editing (FLEURS he_il + inserted stutters)

60 utterances, 2 stutters inserted in each. Recogniser: ctc.

| mode | word_rep removed | sound_rep removed | prolongation removed | block removed | real speech cut (stuttered input) | utterances with >50 ms real speech cut | real speech cut (fluent input) |
|---|---|---|---|---|---|---|---|
| gentle | 14% | 6% | 59% | 49% | 12.32s total | 23% | 11.41s total |
| full | 15% | 9% | 67% | 65% | 17.98s total | 35% | 17.37s total |
| strong | 15% | 11% | 68% | 77% | 19.73s total | 35% | 19.21s total |

## Examples (examples/NN-before.ogg / NN-after.ogg, full mode)

**01** inserted [('sound_rep', 'מיגרמניה'), ('sound_rep', 'הברי')], real speech cut 0.000s
- text: "הנמל היה האתר של סכסוך  ימי מפורסם מ-1889 כאשר שבע אוניות מגרמניה, ארה""ב ובריטניה סירבו לצאת את הנמל."
- heard: האנמן היה ט של סכוך ימיםמפוסם באל [UNK][UNK]ו נותש כאשור שב אוניות ממגרמניה צות התברית פיברטני סוןלצתאתנמל
- edits: block 6.49-6.93 (breath/strain noise, next to another stutter event)

**02** inserted [('word_rep', 'לעבראתרים'), ('block', 'ברופאא')], real speech cut 0.000s
- text: רולנדו מנדוזה ירה ברובה ה-M16 שלו אל עבר התיירים.
- heard: שלא לעבר תירם לעבר איים הם שש שרונלדמנדוזירב רופיא
- edits: block 4.83-5.7 (breath/strain noise)

**03** inserted [('sound_rep', 'בחומ'), ('block', 'בלסקנה')], real speech cut 0.000s
- text: מומלץ בחום למטיילים לשים לב לסכנה של מזג אוויר קשה שפוקד את האזור מכיוון שהוא עלול לפגוע בתכניות הטיול.
- heard: ומנתייניונב לסקנה של אבר קשה שפוקד את האזוי לכיוון שועלול לפגוע בתוכנטיול
- edits: block 2.25-3.29 (cut-off sound before the gap, inside the word 'ומנתייניונב'); block 3.78-4.2 (breath/strain noise, cut-off sound before the gap); block 4.25-4.73 (breath/strain noise, cut-off sound before the gap); block 4.74-5.18 (breath/strain noise, cut-off sound before the gap); block 5.22-5.7 (breath/strain noise, cut-off sound before the gap); block 5.93-6.24 (breath/strain noise, cut-off sound before the gap, next to another stutter event); block 6.48-6.73 (breath/strain noise, cut-off sound before the gap, next to another stutter event)

**04** inserted [('sound_rep', 'טיול'), ('prolongation', 'חוויות')], real speech cut 0.000s
- text: שיתוף של טיול וירטואלי משותף הוא גם דרך נהדרת להתבונן בטיול ולשתף כיתות עתידיות בחוויות.
- heard: שיתוף של טיטיטיול טואלים משותו א גם ד נדרונין יון לשת קיטות עדידיות חוויות
- edits: block 7.91-8.44 (cut-off sound before the gap); block 8.82-9.18 (breath/strain noise, next to another stutter event); pause 9.91-11.01 (long pause shortened)

**05** inserted [('sound_rep', 'לפני')], real speech cut 0.000s
- text: בין השעות 22:00-23:00 לפי אזור זמן ההרים (MDT), הוצתה שריפה על ידי האסירים בחצר.
- heard: מבתחצזה לפני סו שו
- edits: 

**06** inserted [('prolongation', 'משקיף'), ('sound_rep', 'ויבזזוחנויות')], real speech cut 0.000s
- text: "בישקק תוארה כמתדרדרת למצב של ""אנרכיה"" על ידי משקיף אחד, כשכנופיות שוטטו ברחובות ובזזו חנויות של מוצרי צריכה."
- heard: פישקה תורק כמתררתמצב של מחיה על ידיממשקיף אחד כשכנופיות שותיובחובות ובזזוחנויות ש מוצר צרה
- edits: 

**07** inserted [('word_rep', 'מזרח'), ('word_rep', 'חשיבות')], real speech cut 0.000s
- text: באקלים החם של המזרח התיכון, לבית לא הייתה חשיבות רבה כל כך.
- heard: בהכלים מחם של משל מר תיכון לבית לא הית חשיבת חשיבות רבה כל כך
- edits: block 2.35-2.7 (next to another stutter event)

**08** inserted [('block', 'פותור'), ('sound_rep', 'השובר')], real speech cut 0.000s
- text: דל פוטרו החזיק ביתרון מוקדם במערכה השנייה, אך גם מערכה זו הצריכה שובר שוויון לאחר תוצאה של 6-6.
- heard: דל פותור החזיק בייתרון מוקדם במערכה שניאך גם מערכה זו צרררישור שיוויון לכר תוצה של ששש
- edits: block 1.71-2.65 (breath/strain noise); block 3.14-3.57 (breath/strain noise); block 4.21-4.5 (breath/strain noise); block 11.45-11.91 (breath/strain noise)
