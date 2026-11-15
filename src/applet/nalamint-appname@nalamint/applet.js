// NalaMint App Name — the focused app's name in the menu bar, with a small
// app menu (Show All Windows, Hide, Quit), like the macOS menu bar.

const Applet = imports.ui.applet;
const Cinnamon = imports.gi.Cinnamon;
const PopupMenu = imports.ui.popupMenu;

class AppNameApplet extends Applet.TextApplet {
    constructor(metadata, orientation, panelHeight, instanceId) {
        super(orientation, panelHeight, instanceId);
        this.setAllowedLayout(Applet.AllowedLayout.HORIZONTAL);
        this.tracker = Cinnamon.WindowTracker.get_default();
        this.menuManager = new PopupMenu.PopupMenuManager(this);
        this.menu = new Applet.AppletPopupMenu(this, orientation);
        this.menuManager.addMenu(this.menu);
        this.app = null;
        this.focusId = this.tracker.connect('notify::focus-app', () => this.update());
        this.update();
    }

    update() {
        let app = this.tracker.focus_app;
        // Keep showing the last app while our own menu has focus
        if (!app && this.menu.isOpen)
            return;
        this.app = app;
        this.set_applet_label(app ? app.get_name() : 'Desktop');
    }

    windows() {
        return this.app ? this.app.get_windows().filter(w => !w.is_skip_taskbar()) : [];
    }

    on_applet_clicked() {
        this.menu.removeAll();
        let app = this.app;
        if (app) {
            let name = app.get_name();
            this.menu.addAction('Show All Windows', () => {
                let time = global.get_current_time();
                for (let w of this.windows())
                    w.activate(time);
            });
            this.menu.addAction(`Hide ${name}`, () => {
                for (let w of this.windows())
                    w.minimize();
            });
            this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            this.menu.addAction(`Quit ${name}`, () => {
                let time = global.get_current_time();
                for (let w of this.windows())
                    w.delete(time);
            });
        } else {
            // Cinnamon's own toggle: minimizing every window would also
            // minimize nemo-desktop's windows and kill the desktop right-click
            this.menu.addAction('Show Desktop', () => global.workspace_manager
                .toggle_desktop(global.get_current_time()));
        }
        this.menu.toggle();
    }

    on_applet_removed_from_panel() {
        if (this.focusId)
            this.tracker.disconnect(this.focusId);
        this.focusId = 0;
    }
}

function main(metadata, orientation, panelHeight, instanceId) {
    return new AppNameApplet(metadata, orientation, panelHeight, instanceId);
}
