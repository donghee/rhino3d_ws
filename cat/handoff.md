# Handoff — cat

작업 시작 전에 이 파일을 끝까지 읽고 이어서 진행한다. 작업이 끝나면 아래 "모델 버전 내역"과 "다음 작업"을 갱신한다.

## 현재 상태 (2026-11-11)

- 프로젝트 폴더: Linux `/home/donghee/mnt/norang/rhino3d_ws/cat` = Rhino PC `D:\rhino3d_ws\cat`
- Rhino에 현재 열린 문서: cat_v002 내용 (객체 50개, `D:/rhino3d_ws/cat/cat_v002.3dm`으로 저장함)
- Grasshopper에 `cat_rig_v003.gh`가 열려 있고 꼬리 흔들기(`wag_play`)가 재생 중이다. `hide_doc`이 켜져 있어 Rhino 문서의 `Cat` 레이어는 숨겨진 상태다(리그 미리보기만 보임).
- 스크립트는 시작할 때 문서의 모든 객체와 Default 외 레이어를 지운 뒤 고양이를 만든다(빈 문서에서 다시 만들어도 같은 결과).

## 모델 버전 내역

| 버전 | 날짜 | 변경 내용 | 파일 |
|---|---|---|---|
| v001 | 2026-11-11 | 최초 생성. 앉아 있는 브리티쉬 숏헤어(블루그레이 털, 구리색 큰 눈, 통통한 볼, 작고 둥근 귀, 짧고 굵은 꼬리가 몸 오른쪽을 감아 앞발 옆까지). 부위: 엉덩이·허벅지·뒷발, 가슴·목털(Ruff), 앞다리·앞발, 머리·볼·수염패드·턱·콧등, 코·입, 눈(홍채·세로 동공·하이라이트), 귀(바깥/안쪽, 회전면), 수염 6개, 꼬리. 객체 39개, 레이어 `Cat::Fur/Eye/Pupil/Highlight/Nose/EarInner/Mouth/Whisker`. 단위 mm, 높이 약 45, 정면 -Y. | `cat_v001.{3dm,jpg,py,png}` |
| v002 | 2026-11-11 | 눈에서 레이저 발사. 두 동공 앞에서 빨간 빔(흰빛 심 r0.18 + 반투명 붉은 글로우 r0.45→0.75, 발광 재질)이 앞쪽 아래로 뻗어 바닥 (0,-52,0)에서 만남. 눈 앞 플레어, 바닥 충돌 지점 글로우와 그을린 자국 추가. 새 레이어 `Cat::LaserCore/LaserGlow/Scorch`. 객체 50개. | `cat_v002.{3dm,jpg,py,png}` |


## Grasshopper 리그

| 버전 | 날짜 | 내용 | 파일 |
|---|---|---|---|
| rig v001 | 2026-11-11 | v002를 움직이는 GH 정의. 쉬는 자세는 `src` 패널의 .3dm(기본 `cat_v002.3dm`)에서 읽고, Python 3 컴포넌트 `CatRig`가 부품을 변형해 Custom Preview로 보여 준다. | `cat_rig_v001.gh`, `cat_rig_script_v001.py`(컴포넌트 코드), `cat_rig_v001.py`(.gh 생성 스크립트) |
| rig v002 | 2026-11-11 | 수염 슬라이더 추가: `whisker_lift`, `whisker_spread`. | `cat_rig_v002.gh`, `cat_rig_script_v002.py`, `cat_rig_v002.py` |
| rig v003 | 2026-11-11 | 꼬리 흔들기 애니메이션 추가: `wag_amp`, `wag_speed`, `wag_t`, `wag_play`. | `cat_rig_v003.gh`, `cat_rig_script_v003.py`, `cat_rig_v003.py` |

- 슬라이더(좌우는 고양이 기준, 고양이는 -Y를 보므로 왼쪽 = +X):
  `head_yaw` ±45°(목 피벗 (0,-5,28)), `head_nod` ±30°(+ = 아래), `head_tilt` ±25°, `ear_l`/`ear_r` -15~45°(+ = 바깥으로 젖힘), `pupil` 0.3~2.5(동공 폭 배율),
  `paw_l`/`paw_r` 0~90°(어깨 피벗에서 앞발 들기), `tail_unwrap` -20~90°(꼬리 감김 풀기), `tail_lift` 0~25mm(꼬리 끝 들기), `breath` 0~1(가슴·엉덩이 5% 팽창), `whisker_lift` -30~30°(+ = 수염 끝 위로, v002), `whisker_spread` -10~20°(+ = 위·아래 수염을 부채꼴로 벌림, v002).
- 꼬리 흔들기(v003): 꼬리 마디마다 시간차(0.6 rad)를 두고 Z축으로 돌려 물결처럼 흔든다. 몸을 뚫지 않도록 바깥쪽으로만(0~최대) 흔든다.
  `wag_amp` 0~60°(최대 펼침 정도), `wag_speed` 0.1~3 Hz, `wag_t` 0~10 s(재생을 끄면 이 시점의 자세를 보여 줌 → 프레임 뽑기용), `wag_play` 토글(켜면 시스템 시계로 약 25fps 자동 재생, `ScheduleSolution(40ms)`).
  한 프레임 계산은 약 25~35ms(리그 + 미리보기). 파일을 처음 읽을 때만 약 0.5s.
- 토글: `laser`(빔을 머리 방향으로 다시 계산, 바닥에 닿으면 충돌점·그을림 생성), `hide_doc`(Rhino 문서의 `Cat` 레이어를 숨겨 겹침 방지. 끄면 다시 보임).
- 다시 만들기: `rmcp.py run cat/cat_rig_v003.py` (`cat_rig_script_v003.py`를 읽어 새 GH 문서를 만들고 `cat_rig_v003.gh`로 저장. 기존 파일이 있으면 덮어쓰므로 바꿀 때는 다음 번호로 새로 만든다).
- 굽기(bake)는 아직 없다. 포즈를 모델로 남기려면 Custom Preview 대신 `G` 출력을 bake하거나 기능을 추가한다.

## 메모 (기술)

- 회전면(RevSurface)·원뿔 Brep을 비균등 스케일하면 Brep이 무효가 되어 AddBrep이 실패한다 → `ToNurbsSurface().ToBrep()`로 바꾼 뒤 스케일한다.
- GH Python 3 컴포넌트를 코드로 만들 때: `SetParametersFromScript()`는 입력/출력을 만들지 않는다 → `CreateParameter` + `RegisterInputParam/RegisterOutputParam`로 직접 만들고 그 뒤에 `SetSource`. 스크립트 앞부분에 여러 줄 연속 문장(8칸 들여쓴 이어지는 줄)이 있으면 "unindent does not match" 오류가 나므로 한 줄로 쓴다. `GH_SliderAccuracy`는 `Grasshopper.GUI.Base`에 있다.
- `doc.Objects.Count`(및 save_doc가 알려주는 objects 수)는 지운 객체까지 세는 것으로 보인다. 실제 개수는 `len(list(doc.Objects))`나 저장 파일을 `File3dm.Read`로 읽어 확인한다(v001: 39개).

## 다음 작업 / 메모

- 리그 아이디어: 애니메이션 프레임 이미지/영상 내보내기(`wag_t`를 바꿔 가며 캡처), 포즈 bake 토글, 눈동자 시선(좌우), 입 벌리기, 몸통 기울기, 포즈 프리셋/애니메이션.
- 아이디어: 털 색 미세 조정(배·가슴 약간 밝게), 눈꺼풀/눈두덩, 다른 자세(식빵 자세, 누운 자세), 바닥 쿠션, STL 내보내기(`rmcp.py stl cat`).
