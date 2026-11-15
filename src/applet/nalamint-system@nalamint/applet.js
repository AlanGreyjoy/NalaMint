// NalaMint System Menu: the logo menu at the left of the menu bar, like the
// Apple menu. Restart, Shut Down and Log Out go through cinnamon-session-quit,
// which asks for confirmation first; Sleep and Lock Screen act at once.

const Applet = imports.ui.applet;
const PopupMenu = imports.ui.popupMenu;
const Settings = imports.ui.settings;
const Util = imports.misc.util;
const { Cinnamon, Gio, GLib } = imports.gi;

// Opens the first installed app of `ids`, else runs `fallback`
function launch(ids, fallback) {
    let appSys = Cinnamon.AppSystem.get_default();
    for (let id of ids) {
        let app = appSys.lookup_app(id);
        if (app) {
            app.activate();
            return;
        }
    }
    if (fallback)
        Util.spawn(fallback);
}

function lockScreen() {
    // Same as the Mint menu: the away-message dialog if the user enabled it
    let settings = new Gio.Settings({ schema_id: 'org.cinnamon.desktop.screensaver' });
    if (settings.get_boolean('ask-for-away-message'))
        Util.spawn(['cinnamon-screensaver-lock-dialog']);
    else
        Util.spawn(['cinnamon-screensaver-command', '--lock']);
}

class SystemMenuApplet extends Applet.IconApplet {
    constructor(metadata, orientation, panelHeight, instanceId) {
        super(orientation, panelHeight, instanceId);
        this.setAllowedLayout(Applet.AllowedLayout.BOTH);
        this.settings = new Settings.AppletSettings(this, metadata.uuid, instanceId);
        this.settings.bind('menu-icon', 'menuIcon', () => this.updateIcon());
        this.menuManager = new PopupMenu.PopupMenuManager(this);
        this.menu = new Applet.AppletPopupMenu(this, orientation);
        this.menu.actor.add_style_class_name('nalamint-system-menu');
        this.menuManager.addMenu(this.menu);
        this.updateIcon();
        this.buildMenu();
    }

    updateIcon() {
        let icon = this.menuIcon || 'cinnamon-symbolic';
        if (GLib.path_is_absolute(icon))
            this.set_applet_icon_path(icon);
        else if (icon.endsWith('-symbolic'))
            this.set_applet_icon_symbolic_name(icon);
        else
            this.set_applet_icon_name(icon);
    }

    buildMenu() {
        let m = this.menu;
        let separator = () => m.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        m.addAction('About This Computer', () => launch(['mintreport.desktop'], ['cinnamon-settings', 'info']));
        separator();
        m.addAction('System Settings…', () => launch(['cinnamon-settings.desktop'], ['cinnamon-settings']));
        m.addAction('Software Manager…', () => launch(['mintinstall.desktop']));
        separator();
        m.addAction('Force Quit…', () => Util.spawn(['gnome-system-monitor', '--show-processes-tab']));
        separator();
        m.addAction('Sleep', () => Util.spawn(['systemctl', 'suspend']));
        m.addAction('Restart…', () => Util.spawn(['cinnamon-session-quit', '--reboot']));
        m.addAction('Shut Down…', () => Util.spawn(['cinnamon-session-quit', '--power-off']));
        separator();
        m.addAction('Lock Screen', lockScreen);
        m.addAction(`Log Out ${GLib.get_real_name()}…`, () => Util.spawn(['cinnamon-session-quit', '--logout']));
    }

    on_applet_clicked() {
        this.menu.toggle();
    }

    on_applet_removed_from_panel() {
        this.settings.finalize();
        this.menu.destroy();
    }
}

function main(metadata, orientation, panelHeight, instanceId) {
    return new SystemMenuApplet(metadata, orientation, panelHeight, instanceId);
}
