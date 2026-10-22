"""Main-thread, nonmodal hover/focus help with an explicit F1 alternative."""
import tkinter as tk
import customtkinter as ctk

from equipment_data_manager.ui.help_content import HELP


class Guidance:
    def __init__(self, app, context, manual_help, enabled, level):
        self.app, self.context, self.manual_help = app, context, manual_help
        self.enabled, self.level = enabled, level
        self.widgets = {}
        self.key = 'status'
        self.pending = None
        self.popup = None
        self.hide_pending = None
        self.anchor = None
        app.bind('<F1>', lambda event: self.manual_help(self.key), add='+')
        app.bind('<Escape>', lambda event: self.hide(), add='+')

    def register(self, widget, key):
        if key not in HELP:
            raise KeyError(key)
        self.widgets[widget] = key
        # Bind Tk frames AND children: CTk's normal bind forwards only some
        # events to its canvas/labels. Disabled controls still receive help.
        targets = [widget]
        for target in targets:
            targets.extend(child for child in target.winfo_children() if child not in targets)
            tk.Misc.bind(target, '<Enter>', lambda event, w=widget, k=key: self.schedule(w, k), add='+')
            tk.Misc.bind(target, '<Leave>', lambda event: self.leaving(), add='+')
            tk.Misc.bind(target, '<FocusIn>', lambda event, w=widget, k=key: self.schedule(w, k), add='+')
            tk.Misc.bind(target, '<FocusOut>', lambda event: self.hide(), add='+')
            tk.Misc.bind(target, '<ButtonPress>', lambda event: self.hide(), add='+')
        if isinstance(widget, (ctk.CTkButton,ctk.CTkRadioButton,ctk.CTkCheckBox,ctk.CTkSwitch)):
            widget.tk.call(widget._w, 'configure', '-takefocus', 1)
            def activate(event):
                if widget.cget('state') != 'disabled':
                    action=getattr(widget,'invoke',None) or getattr(widget,'toggle',None)
                    if action is not None:
                        action()
                return 'break'
            for target in targets:
                tk.Misc.bind(target, '<Return>', activate, add='+')
                tk.Misc.bind(target, '<space>', activate, add='+')

    def text(self, key):
        return HELP[key].text(self.level(), self.context(key))

    def schedule(self, widget, key):
        self.hide()
        if key in ("powerbi", "legacy"):
            key = "legacy" if widget.get().startswith("Legacy") else "powerbi"
        self.key, self.anchor = key, widget
        if self.enabled():
            self.pending = self.app.after(550, self.show)

    def show(self):
        if self.pending is not None:
            self.app.after_cancel(self.pending)
            self.pending = None
        if not self.enabled() or self.anchor is None or not self.anchor.winfo_exists():
            return
        # A plain Tk popup avoids CTkToplevel's delayed titlebar callbacks after
        # short-lived tips close. The main application remains CustomTkinter.
        popup = tk.Toplevel(self.app)
        self.popup = popup
        popup.withdraw()
        popup.overrideredirect(True)
        popup.configure(background='#172B4D')
        popup.bind('<F1>',lambda event:self.manual_help(self.key))
        popup.bind('<Escape>',lambda event:self.hide())
        screen_w,screen_h=self.app.winfo_screenwidth(),self.app.winfo_screenheight()
        scale=ctk.ScalingTracker.get_widget_scaling(self.app)
        content_width=int(min(420*scale,screen_w-40)-24)
        body_height=int(max(64,min(360*scale,screen_h-110*scale)))
        family=ctk.ThemeManager.theme['CTkFont']['family']
        font=(family,-max(12,int(13*scale)))
        tk.Label(popup,text=HELP[self.key].title,foreground='white',background='#172B4D',
            wraplength=content_width,font=(family,-max(13,int(14*scale)),'bold')).pack(padx=12,pady=(8,2))
        body=tk.Frame(popup,width=content_width,height=body_height,background='#172B4D')
        body.pack(padx=12,pady=2)
        body.pack_propagate(False)
        text=tk.Text(body,wrap='word',background='#172B4D',foreground='white',font=font,
            relief='flat',borderwidth=0,highlightthickness=0)
        scroll=tk.Scrollbar(body,command=text.yview)
        scroll.pack(side='right',fill='y')
        text.configure(yscrollcommand=scroll.set)
        text.pack(side='left',fill='both',expand=True)
        text.insert('1.0',self.text(self.key))
        text.configure(state='disabled')
        tk.Label(popup,text='F1: full help | Esc: close',foreground='white',background='#172B4D',font=font).pack(padx=12,pady=(2,8))
        popup.bind('<Leave>',lambda event:self.leaving(),add='+')
        popup.update_idletasks()
        width, height = popup.winfo_reqwidth(), popup.winfo_reqheight()
        screen_w, screen_h = self.app.winfo_screenwidth(), self.app.winfo_screenheight()
        # Prefer below; move above near the bottom, and clamp at screen edges.
        x = min(max(8, self.anchor.winfo_rootx()), max(8, screen_w - width - 8))
        y = self.anchor.winfo_rooty() + self.anchor.winfo_height() + 8
        if y + height > screen_h - 8:
            y = max(8, self.anchor.winfo_rooty() - height - 8)
        tk.Toplevel.geometry(popup,f'+{x}+{y}')
        popup.deiconify()
        popup.lift()
        # No auto-expiry: it remains readable until pointer/focus leaves, click,
        # Escape, navigation or Guided Mode changes. It never grabs focus.

    def leaving(self):
        if self.hide_pending is not None:
            self.app.after_cancel(self.hide_pending)
        self.hide_pending=self.app.after(120,self.hide_if_outside)

    def hide_if_outside(self):
        self.hide_pending=None
        x,y=self.app.winfo_pointerxy()
        for widget in (self.anchor,self.popup):
            if widget is not None and widget.winfo_exists():
                if widget.winfo_rootx()<=x<=widget.winfo_rootx()+widget.winfo_width() and widget.winfo_rooty()<=y<=widget.winfo_rooty()+widget.winfo_height():
                    return
        self.hide()

    def hide(self):
        if self.hide_pending is not None:
            self.app.after_cancel(self.hide_pending)
            self.hide_pending=None
        if self.pending is not None:
            self.app.after_cancel(self.pending)
            self.pending = None
        if self.popup is not None:
            self.popup.destroy()
            self.popup = None
