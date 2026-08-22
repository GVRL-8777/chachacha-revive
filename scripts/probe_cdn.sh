#!/bin/sh
# 살아 있는 호스트 + 알려진 경로 규칙을 조합해 카탈로그를 찾는다.
HOSTS="c2.img.netmarble.kr c3.img.netmarble.kr cr.img.mcdn.netmarble.kr img.netmarble.kr dn.netmarble.net cdn.netmarble.com"
BASES="cr/Real/Android chachachaf/Real/Android chachachaf/cr/Real/Android cr/Release cr/Test mobile/chachacha/Real/Android chachacha/Real/Android"
CATS="Catalogue/AssetCatalogue.txt Catalogue/AssetCatalogue_1.4.3.txt Catalogue/AssetCatalogue_7.7.0.txt"
for h in $HOSTS; do
  for b in $BASES; do
    for c in $CATS; do
      u="http://$h/$b/$c"
      code=$(curl -s -o /tmp/cdnprobe -m 8 -w "%{http_code}" "$u" 2>/dev/null)
      sz=$(wc -c < /tmp/cdnprobe 2>/dev/null)
      # 404 안내 페이지(1245B)와 실제 콘텐츠 구분
      if [ "$code" = "200" ] && [ "$sz" -gt 0 ]; then
        echo "★★ $code $sz  $u"
      fi
    done
  done
done
echo "탐색 완료"
