#!/bin/bash
echo "SLIDE SPEAKER SCRIPT VERIFICATION"
echo "=================================="
echo ""

for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31 32 33 34 35 36 37 38 39 40 41 42 43 44 45
do
    count=$(sed -n "/^## Slide $i:/,/^## Slide /p" CHALLENGE2_FIRE_DATA_PRESENTATION.md | grep -c "Speaker Script")
    if [ $count -eq 0 ]; then
        echo "Slide $i: ❌ NO SCRIPT"
    else
        echo "Slide $i: ✅ $count script(s)"
    fi
done

echo ""
echo "Total speaker script sections:"
grep -c "Speaker Script" CHALLENGE2_FIRE_DATA_PRESENTATION.md
