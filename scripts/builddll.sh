#!/bin/sh
# Assembly-CSharp.dll 을 처음부터 다시 만든다.
#
#   mgbase/Assembly-CSharp.dll   patchcn.exe 까지 끝난 것 (한국어화 포함)
#     -> tunnelfix.exe           터널 세트 · 번들 주소 · 번들 이름표
#     -> notutorial.exe          중국어 도움말 팝업 끄기
#     -> rankfix.exe             소셜 없이도 주간순위가 그려지게
#     -> invitefix.exe           초대 목록에 이웃 5명
#     -> shopfix.exe             결제창 원화 표시 · 즉시 결제
#     -> modesfix.exe            중국판이 꺼 둔 모드 켜기(CHA_MODES)
#     -> tradefix.exe            되팔기 팝업의 널 딕셔너리 초기화
#     -> titlefix.exe            타이틀이 그냥 지나쳐 버리는 것 (CHA_TITLE_FRAMES)
#     -> x77/.../Managed/
#
# 로컬 전용(서버 없는) 빌드는 여기서 나온 ACCN.dll 을 한 번 더 손본다.
#   ./localfix.exe ACCN.dll ACLOCAL.dll ChaLocal.dll mgbase
# 그건 chatool 이 알아서 한다:  chatool build --mode local
# (자세한 것은 LOCALAPK.md)
#
# 순서를 지켜야 한다. tunnelfix 가 만든 __ChaResLoad 를 도움말 팝업도 쓴다.
# scripts/ 안에 있지만 일감은 저장소 뿌리에서 돕니다
cd "$(dirname "$0")/.."
set -e
./tunnelfix.exe mgbase/Assembly-CSharp.dll ACtmp.dll mgbase "${CHA_BUNDLE_URL:-http://127.0.0.1:8888/bundle/pack.unity3d}" | tail -3
./notutorial.exe ACtmp.dll ACtmp2.dll | tail -2
./rankfix.exe ACtmp2.dll ACtmp3.dll | tail -2
./invitefix.exe ACtmp3.dll ACtmp4.dll | tail -2
./shopfix.exe ACtmp4.dll ACtmp5.dll | tail -3
./modesfix.exe ACtmp5.dll ACtmp6.dll "${CHA_MODES:-hurdle,tradecar}" | tail -3
./tradefix.exe ACtmp6.dll ACtmp7.dll | tail -2
./titlefix.exe ACtmp7.dll ACtmp8.dll "${CHA_TITLE_FRAMES:-180}" | tail -3
 ./pausefix.exe ACtmp8.dll ACCN.dll mgbase | tail -3
rm -f ACtmp.dll ACtmp2.dll ACtmp3.dll ACtmp4.dll ACtmp5.dll ACtmp7.dll ACtmp8.dll
cp ACCN.dll x77/assets/bin/Data/Managed/Assembly-CSharp.dll
echo "x77 에 반영 완료"
