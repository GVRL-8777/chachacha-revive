# -*- coding: utf-8 -*-
"""파일·폴더 고르는 창을 띄웁니다.

런처는 **내 PC 에서 돌아가는 서버**라, 여기서 tkinter 창을 띄우면 사용자
앞에 그대로 뜹니다. 브라우저의 파일 상자로는 '저장할 폴더' 를 고를 수
없어서(보안상 경로를 안 알려 줍니다) 이 길을 씁니다.

요청마다 새 스레드에서 불리므로 `Tk()` 도 그때그때 만들고 바로 부숩니다.
하나를 붙들고 있으면 두 번째 창이 안 뜹니다.

창을 못 띄우는 자리(원격·헤드리스)에서는 조용히 None 을 돌려주고, 부르는
쪽이 기본 폴더로 물러섭니다.
"""
import os


def _root():
    import tkinter as tk
    r = tk.Tk()
    r.withdraw()
    r.attributes('-topmost', True)
    r.update()
    return r


def folder(title='폴더를 고르세요', start=None):
    try:
        from tkinter import filedialog
        r = _root()
        try:
            p = filedialog.askdirectory(title=title, initialdir=start or None,
                                        mustexist=False)
        finally:
            r.destroy()
        return p or None
    except Exception:
        return None


def save_file(title='저장할 자리를 고르세요', start=None, name='',
              ext='.json', kind='세이브 파일'):
    try:
        from tkinter import filedialog
        r = _root()
        try:
            p = filedialog.asksaveasfilename(
                title=title, initialdir=start or None, initialfile=name,
                defaultextension=ext,
                filetypes=[(kind, '*' + ext), ('모든 파일', '*.*')])
        finally:
            r.destroy()
        return p or None
    except Exception:
        return None


def open_file(title='파일을 고르세요', start=None, ext='.json',
              kind='세이브 파일'):
    try:
        from tkinter import filedialog
        r = _root()
        try:
            p = filedialog.askopenfilename(
                title=title, initialdir=start or None,
                filetypes=[(kind, '*' + ext), ('모든 파일', '*.*')])
        finally:
            r.destroy()
        return p or None
    except Exception:
        return None


def available():
    try:
        import tkinter                                    # noqa: F401
        return True
    except Exception:
        return False


def default_dir(here):
    d = os.path.join(here, 'export')
    os.makedirs(d, exist_ok=True)
    return d
