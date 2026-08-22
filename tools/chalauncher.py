# -*- coding: utf-8 -*-
"""차차차 상태 파일을 브라우저에서 고친다.

서버로 갈 데이터(chastate.json) 하나를 통째로 편집하는 웹 화면이다.
파이썬은 이 컴퓨터에만 있으면 되고, 다른 기기는 브라우저로 들어오면 된다.

  python chalauncher.py            # http://localhost:8080
  python chalauncher.py 0.0.0.0    # 같은 망의 다른 기기에서도 접속

저장을 누르면 chastate.json 이 새로 쓰이고, 게임 서버는 그 파일이 바뀐 것을
알아채 다음 요청부터 새 값으로 답한다(서버를 껐다 켤 필요 없다).
"""
import sys

from nicegui import ui

import chastate as S

HOST = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 8080

CLASSES = ["C", "B", "A", "S", "R"]
TUNE_KEYS = [("accel", "가속"), ("speed", "속도"), ("oil", "연비")]


def build(state, mark):
    """탭 전체를 그린다. mark 는 '고쳤음' 표시를 켜는 함수."""

    def num(label, holder, key, maximum, suffix=''):
        def on(e):
            try:
                v = int(e.value or 0)
            except (TypeError, ValueError):
                v = 0
            holder[key] = max(0, min(maximum, v))
            mark()
        return ui.number(label=label, value=holder.get(key, 0),
                         min=0, max=maximum, step=1,
                         on_change=on, suffix=suffix) \
                 .props('outlined dense').classes('w-56')

    def text(label, holder, key, area=False):
        def on(e):
            holder[key] = e.value or ''
            mark()
        f = ui.textarea if area else ui.input
        return f(label=label, value=holder.get(key, ''), on_change=on) \
                 .props('outlined dense').classes('w-full')

    with ui.tabs().classes('w-full') as tabs:
        t_player = ui.tab('플레이어')
        t_cars = ui.tab('자동차')
        t_drivers = ui.tab('드라이버')
        t_items = ui.tab('아이템 · 스킬')
        t_misc = ui.tab('초대 · 수신 · 공지')

    with ui.tab_panels(tabs, value=t_player).classes('w-full'):

        # ---------------- 플레이어 ----------------
        with ui.tab_panel(t_player):
            with ui.column().classes('gap-6 w-full'):
                ui.label('보유').classes('text-sm text-grey-7')
                with ui.row().classes('gap-4 items-center flex-wrap'):
                    num('골드', state['player'], 'gold', S.MAX_GOLD)
                    num('트로피', state['player'], 'trophy', S.MAX_TROPHY)
                    num('타이어', state['player'], 'tire', S.MAX_TIRE)
                ui.label('타이어는 998 이 상한이다. 999 가 되면 게임이 초대를 막는다.') \
                    .classes('text-xs text-grey-6 -mt-4')

                ui.separator()
                ui.label('정체').classes('text-sm text-grey-7')
                with ui.row().classes('gap-4 items-center flex-wrap'):
                    text('닉네임', state['player'], 'nickName').classes('w-56')

                    def on_car(e):
                        state['player']['car'] = e.value
                        mark()
                    ui.select([n for _i, n, _c in S.CARS],
                              label='지금 타는 차',
                              value=state['player'].get('car', 'AVEO'),
                              on_change=on_car).props('outlined dense').classes('w-56')

                    def on_drv(e):
                        state['player']['driver'] = int(e.value)
                        mark()
                    ui.select({d: '%d · %s' % (d, n) for d, n in S.DRIVERS},
                              label='드라이버',
                              value=state['player'].get('driver', 1),
                              on_change=on_drv).props('outlined dense').classes('w-56')

                ui.separator()
                ui.label('기록 — 주간순위에 그대로 올라간다').classes('text-sm text-grey-7')
                with ui.row().classes('gap-4 items-center flex-wrap'):
                    num('주행 최고점', state['records'], 'bestScore', S.MAX_TROPHY)
                    num('장애물 최고점', state['records'], 'bestScoreHurdle', S.MAX_TROPHY)
                    num('지난주 기록', state['records'], 'prevScore', S.MAX_TROPHY)
                    num('최장 거리', state['records'], 'maxDistance', 99999999, ' m')
                    num('플레이 횟수', state['records'], 'playCount', 99999999)

        # ---------------- 자동차 ----------------
        with ui.tab_panel(t_cars):
            owned = set(state['carsOwned'])

            def bulk(names):
                state['carsOwned'] = list(names)
                mark()
                ui.navigate.reload()

            with ui.row().classes('gap-2 items-center q-mb-md flex-wrap'):
                ui.label('보유를 끄면 자동차 샵에 매물로 뜬다.').classes('text-xs text-grey-6')
                ui.space()
                ui.button('전부 보유',
                          on_click=lambda: bulk([n for _i, n, _c in S.CARS])) \
                    .props('flat dense')
                ui.button('기본차만',
                          on_click=lambda: bulk(['AVEO'])).props('flat dense')

            with ui.scroll_area().classes('w-full').style('height: 58vh'):
                for no, name, start in S.CARS:
                    tune = state['carTune'].setdefault(name, {})
                    with ui.row().classes(
                            'items-center gap-3 w-full q-py-xs').style(
                            'border-bottom:1px solid rgba(128,128,128,.15)'):

                        def on_own(e, nm=name):
                            if e.value:
                                if nm not in state['carsOwned']:
                                    state['carsOwned'].append(nm)
                            elif nm in state['carsOwned']:
                                state['carsOwned'].remove(nm)
                            mark()
                        ui.switch(value=name in owned, on_change=on_own) \
                            .props('dense')

                        ui.label('%2d' % no).classes(
                            'text-xs text-grey-6 w-8 text-right')
                        ui.label(name).classes('w-40')

                        def on_cls(e, nm=name):
                            state['carClass'][nm] = e.value
                            mark()
                        ui.select(CLASSES, value=state['carClass'].get(name, start),
                                  on_change=on_cls) \
                            .props('outlined dense').classes('w-20')

                        for key, lab in TUNE_KEYS:
                            def on_tune(e, t=tune, k=key):
                                try:
                                    t[k] = max(0, min(3, int(e.value or 0)))
                                except (TypeError, ValueError):
                                    t[k] = 0
                                mark()
                            ui.number(label=lab, value=tune.get(key, 0),
                                      min=0, max=3, step=1, on_change=on_tune) \
                                .props('outlined dense').classes('w-24')

        # ---------------- 드라이버 ----------------
        with ui.tab_panel(t_drivers):
            ui.label('끄면 캐릭터 상점에서 사야 한다.').classes('text-xs text-grey-6 q-mb-md')
            with ui.grid(columns=3).classes('gap-2 w-full'):
                for no, name in S.DRIVERS:
                    def on_drv_own(e, d=no):
                        if e.value:
                            if d not in state['driversOwned']:
                                state['driversOwned'].append(d)
                        elif d in state['driversOwned']:
                            state['driversOwned'].remove(d)
                        mark()
                    ui.switch('%d · %s' % (no, name),
                              value=no in state['driversOwned'],
                              on_change=on_drv_own).props('dense')

        # ---------------- 아이템 · 스킬 ----------------
        with ui.tab_panel(t_items):
            ui.label('아이템 — 상점의 일곱 칸. 서버 응답은 아직 안 붙였다.') \
                .classes('text-sm text-grey-7')
            with ui.grid(columns=2).classes('gap-3 w-full q-mb-lg'):
                for code in S.ITEMS:
                    num('%s (%s)' % (S.ITEM_LABEL[code], code),
                        state['items'], code, 999)

            ui.separator()
            ui.label('스킬 — 아직 서버 미구현. 형식만 맞춰 두면 붙일 때 바로 쓴다.') \
                .classes('text-sm text-grey-7')

            skill_box = ui.column().classes('gap-2 w-full')

            def draw_skills():
                skill_box.clear()
                with skill_box:
                    for i, sk in enumerate(state['skills']):
                        with ui.row().classes('items-center gap-3'):
                            def on_no(e, s=sk):
                                s['skill'] = int(e.value or 0); mark()
                            ui.number(label='스킬 번호', value=sk.get('skill', 1),
                                      min=1, max=99, on_change=on_no) \
                                .props('outlined dense').classes('w-32')

                            def on_car2(e, s=sk):
                                s['car'] = e.value; mark()
                            ui.select([n for _i, n, _c in S.CARS], label='차',
                                      value=sk.get('car', 'AVEO'),
                                      on_change=on_car2) \
                                .props('outlined dense').classes('w-40')

                            def on_lv(e, s=sk):
                                s['level'] = int(e.value or 1); mark()
                            ui.number(label='레벨', value=sk.get('level', 1),
                                      min=1, max=3, on_change=on_lv) \
                                .props('outlined dense').classes('w-24')

                            def on_eq(e, s=sk):
                                s['equipped'] = bool(e.value); mark()
                            ui.switch('장착', value=sk.get('equipped', False),
                                      on_change=on_eq).props('dense')

                            def on_del(_, idx=i):
                                state['skills'].pop(idx); mark(); draw_skills()
                            ui.button(icon='delete', on_click=on_del) \
                                .props('flat dense round')

            def add_skill():
                state['skills'].append(
                    {'skill': 1, 'car': 'AVEO', 'level': 1, 'equipped': False})
                mark()
                draw_skills()

            draw_skills()
            ui.button('스킬 추가', icon='add', on_click=add_skill) \
                .props('flat dense').classes('q-mt-sm')

        # ---------------- 초대 · 수신 · 공지 ----------------
        with ui.tab_panel(t_misc):
            with ui.column().classes('gap-6 w-full'):
                ui.label('초대').classes('text-sm text-grey-7')
                with ui.row().classes('gap-4 items-center'):
                    num('누적 횟수', state['invite'], 'count', 9999)
                ui.label('30회에 미아우(CAT), 50회에 허미(Hummer)를 받는다.') \
                    .classes('text-xs text-grey-6 -mt-4')

                ui.separator()
                ui.label('휴면 복귀').classes('text-sm text-grey-7')
                with ui.row().classes('gap-4 items-center'):
                    num('쉰 날수', state['dormancy'], 'days', 3650, ' 일')

                    def on_taken(e):
                        state['dormancy']['rewardTaken'] = bool(e.value)
                        mark()
                    ui.switch('보상 받음',
                              value=state['dormancy'].get('rewardTaken', False),
                              on_change=on_taken).props('dense')

                ui.separator()
                ui.label('수신함').classes('text-sm text-grey-7')
                present_box = ui.column().classes('gap-2 w-full')

                def draw_presents():
                    present_box.clear()
                    with present_box:
                        for i, pr in enumerate(state['presents']):
                            with ui.row().classes('items-center gap-3'):
                                def on_type(e, p=pr):
                                    p['type'] = e.value; mark()
                                ui.select({'tire': '타이어', 'trophy': '트로피',
                                           'gold': '골드'},
                                          label='종류', value=pr.get('type', 'tire'),
                                          on_change=on_type) \
                                    .props('outlined dense').classes('w-32')

                                def on_cnt(e, p=pr):
                                    p['count'] = int(e.value or 0); mark()
                                ui.number(label='개수', value=pr.get('count', 1),
                                          min=1, max=9999, on_change=on_cnt) \
                                    .props('outlined dense').classes('w-28')

                                def on_from(e, p=pr):
                                    p['from'] = e.value; mark()
                                ui.input(label='보낸 사람',
                                         value=pr.get('from', ''),
                                         on_change=on_from) \
                                    .props('outlined dense').classes('w-48')

                                def on_del2(_, idx=i):
                                    state['presents'].pop(idx)
                                    mark(); draw_presents()
                                ui.button(icon='delete', on_click=on_del2) \
                                    .props('flat dense round')

                def add_present():
                    state['presents'].append(
                        {'type': 'tire', 'count': 5, 'from': '지나가는 행인'})
                    mark(); draw_presents()

                draw_presents()
                ui.button('선물 추가', icon='add', on_click=add_present) \
                    .props('flat dense')

                ui.separator()
                ui.label('공지사항 — 로비에서 읽는 글').classes('text-sm text-grey-7')
                text('제목', state['notice'], 'title')
                text('내용', state['notice'], 'body', area=True).classes('w-full')

                ui.separator()
                ui.label('스위치').classes('text-sm text-grey-7')

                def on_nw(e):
                    state['flags']['newWeek'] = bool(e.value)
                    mark()
                ui.switch('지난주 순위 팝업 띄우기',
                          value=state['flags'].get('newWeek', False),
                          on_change=on_nw).props('dense')


@ui.page('/')
def index():
    state = S.load()
    dirty = {'v': False}

    ui.colors(primary='#C8511B')
    dark = ui.dark_mode()

    def mark():
        dirty['v'] = True
        status.text = '고친 내용 있음'
        status.classes(replace='text-sm text-orange-8')

    def do_save():
        S.clamp(state)
        S.save(state)
        dirty['v'] = False
        status.text = '저장됨'
        status.classes(replace='text-sm text-green-8')
        ui.notify('chastate.json 에 저장했다. 게임 서버가 바로 읽는다.',
                  position='bottom')

    def do_reload():
        ui.navigate.reload()

    def do_reset():
        S.save(S.default())
        ui.notify('기본값으로 되돌렸다.', position='bottom')
        ui.navigate.reload()

    with ui.header().classes('items-center gap-3 q-px-lg').style(
            'background:transparent; border-bottom:1px solid rgba(128,128,128,.2)'):
        ui.label('차차차 상태').classes('text-lg')
        ui.label(S.STATE_PATH).classes('text-xs text-grey-6')
        ui.space()
        status = ui.label('불러옴').classes('text-sm text-grey-6')
        ui.button('저장', icon='save', on_click=do_save).props('unelevated dense')
        ui.button(icon='refresh', on_click=do_reload).props('flat dense round') \
            .tooltip('파일에서 다시 읽기')
        ui.button(icon='restart_alt', on_click=do_reset).props('flat dense round') \
            .tooltip('기본값으로')
        ui.button(icon='dark_mode', on_click=dark.toggle) \
            .props('flat dense round').tooltip('밝기')

    with ui.column().classes('w-full max-w-5xl mx-auto q-pa-lg gap-4'):
        build(state, mark)


print('차차차 상태 런처  ->  http://%s:%d'
      % ('localhost' if HOST in ('127.0.0.1', '0.0.0.0') else HOST, PORT))
print('  브라우저가 저절로 안 열리면 위 주소를 직접 열면 된다.')
print('  다른 기기에서도 쓰려면:  python chalauncher.py 0.0.0.0')

# show=True 여야 기본 브라우저가 저절로 열린다.
ui.run(host=HOST, port=PORT, title='차차차 상태', reload=False,
       show=True, favicon='🏁')
