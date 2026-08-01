#!/usr/bin/env python3.14

import re
import typing

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, Gdk, GLib, Graphene, GObject

from pathlib import Path

import time

from subprocess import run

import sys

def boot(_, index) -> None:
	run(["/usr/bin/env", "sh", "-c", f"grub-reboot {index} && reboot"], check=False) # TODO: выдавать ошибку

def new_power_button(image_path: str, name: str="", tooltip_text: str="", pixel_size: int=24) -> Gtk.Button:
	power_texture = Gdk.Texture.new_from_filename(image_path)
	power_image = Gtk.Image.new_from_paintable(power_texture)
	power_image.set_pixel_size(pixel_size)
	power_image.set_name("power-image")
	power_image.add_css_class("image")

	power_button = Gtk.Button(name=name, tooltip_text=tooltip_text)
	power_button.add_css_class("button")

	power_button.set_child(power_image)

	return power_button

class BlurredBackground(Gtk.Widget):
	def __init__(self, image_path: str, blur_radius: float=15.0):
		super().__init__()

		self.texture = Gdk.Texture.new_from_filename(image_path)

		self.blur_radius = blur_radius

	def do_snapshot(self, snapshot: Gtk.Snapshot):
		width = self.get_width()
		height = self.get_height()

		bounds = Graphene.Rect.alloc()
		bounds.init(0, 0, width, height)

		snapshot.push_blur(self.blur_radius)

		snapshot.append_texture(self.texture, bounds)

		snapshot.pop()

class PowerControlWidget(Gtk.Widget):
	__gsignals__: typing.ClassVar = {
		'poweroff': (GObject.SignalFlags.RUN_FIRST, None, ()),
		'restart': (GObject.SignalFlags.RUN_FIRST, None, ()),
		'sleep': (GObject.SignalFlags.RUN_FIRST, None, ()),
		'exit': (GObject.SignalFlags.RUN_FIRST, None, ()),
	}

	def __init__(self, work_dir: Path) -> None:
		super().__init__()

		layout = Gtk.BoxLayout(orientation=Gtk.Orientation.HORIZONTAL)

		self.set_layout_manager(layout)

		self.power_button = new_power_button(str(work_dir / "icons/power.svg"), name="power-button", tooltip_text="Выключить компьютер")
		self.power_button.connect("clicked", self.poweroff)

		self.restart_button = new_power_button(str(work_dir / "icons/restart.svg"), name="restart-button", tooltip_text="Перезагрузить компьютер")
		self.restart_button.connect("clicked", self.restart)

		self.sleep_button = new_power_button(str(work_dir / "icons/sleep.svg"), name="sleep-button", tooltip_text="Спящий режим")
		self.sleep_button.connect("clicked", self.sleep)

		self.exit_button = new_power_button(str(work_dir / "icons/exit.svg"), name="exit-button", tooltip_text="Выйти из сессии", pixel_size=28)
		self.exit_button.connect("clicked", self.exit)

		self.power_button.set_parent(self)
		self.restart_button.set_parent(self)
		self.sleep_button.set_parent(self)
		self.exit_button.set_parent(self)

		self.set_halign(Gtk.Align.CENTER)

	def poweroff(self, _) -> None:
		self.emit("poweroff")

	def restart(self, _) -> None:
		self.emit("restart")

	def sleep(self, _) -> None:
		self.emit("sleep")

	def exit(self, _) -> None:
		self.emit("exit")

	def do_dispose(self) -> None:
		self.power_button.unparent()
		self.restart_button.unparent()
		self.sleep_button.unparent()
		self.exit_button.unparent()

		super().do_dispose()

class GrubEntryWidget(Gtk.Widget):
	def __init__(self, work_dir: Path, entry: tuple[str, str], index: int) -> None:
		super().__init__()

		self.layout = Gtk.BoxLayout(orientation=Gtk.Orientation.VERTICAL)
		self.set_layout_manager(self.layout)

		self.button = Gtk.Button()
		self.button.set_parent(self)

		self.center_box = Gtk.CenterBox()

		path = str(work_dir / f"icons/{entry[1]}.svg")

		if not Path(path).exists():
			path = str(work_dir / "icons/question.svg")

		texture = Gdk.Texture.new_from_filename(path)

		self.image = Gtk.Image.new_from_paintable(texture)
		self.image.add_css_class("entry_icon")

		self.image.set_pixel_size(64)

		self.left_label = Gtk.Label(label=entry[0])
		self.left_label.set_halign(Gtk.Align.START)

		self.center_box.set_start_widget(self.image)
		self.center_box.set_center_widget(self.left_label)

		self.button.add_css_class("entry")

		self.button.set_child(self.center_box)

		self.button.connect("clicked", boot, index)

	def do_dispose(self) -> None:
		self.button.unparent()
		self.center_box.unparent()
		self.image.unparent()
		self.left_label.unparent()

		super().do_dispose()

class GrubLoaderWidget(Gtk.Widget):
	def __init__(self, entries: list[tuple[str, str]], work_dir: Path) -> None:
		super().__init__()

		layout = Gtk.BoxLayout(orientation=Gtk.Orientation.VERTICAL)
		self.set_layout_manager(layout)

		self.text = Gtk.Label(label="Выберите OS для загрузки:", name="title")
		self.text.set_halign(Gtk.Align.CENTER)
		self.text.set_parent(self)

		self.scrollable = Gtk.ScrolledWindow()
		self.scrollable.set_vexpand(True)
		self.scrollable.set_margin_bottom(20)
		self.scrollable.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
		self.scrollable.set_overlay_scrolling(False)
		self.scrollable.set_parent(self)

		self.scroll_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

		for i, entry in enumerate(entries):
			button = GrubEntryWidget(work_dir, entry, i)

			self.scroll_box.append(button)

		self.scrollable.set_child(self.scroll_box)

		self.power_control_box = PowerControlWidget(work_dir)
		self.power_control_box.set_parent(self)

	def do_dispose(self) -> None:
		self.text.unparent()
		self.scrollable.unparent()
		self.scroll_box.unparent()
		self.power_control_box.unparent()

		super().do_dispose()

class TimeDateWidget(Gtk.Widget):
	def __init__(self):
		super().__init__()

		layout = Gtk.BoxLayout()
		layout.set_orientation(Gtk.Orientation.VERTICAL)
		self.set_layout_manager(layout)

		self.time_label = Gtk.Label(name="time-label")
		self.time_label.set_parent(self)

		self.date_label = Gtk.Label(name="date-label")
		self.date_label.set_parent(self)

		self.set_vexpand(True)
		self.set_valign(Gtk.Align.CENTER)

		self.update_time()

		GLib.timeout_add(1000, self.update_time)

	def update_time(self) -> bool:
		self.time_label.set_label(time.strftime("%H:%M"))
		self.date_label.set_label(time.strftime("%d %B, %Y"))

		return True

	def do_dispose(self) -> None:
		self.time_label.unparent()
		self.date_label.unparent()

		super().do_dispose()

class UserEntryWidget(Gtk.Widget):
	def __init__(self, user: str) -> None:
		super().__init__()

		layout = Gtk.BoxLayout(orientation=Gtk.Orientation.VERTICAL)
		self.set_layout_manager(layout)

		self.user_label = Gtk.Label(label=user)
		self.user_label.add_css_class("active-user-label")
		self.user_label.set_parent(self)

		self.password_text = Gtk.PasswordEntry(name="password-text", placeholder_text="Введите пароль")
		self.password_text.set_parent(self)

		self.set_halign(Gtk.Align.CENTER)

	def do_dispose(self) -> None:
		self.user_label.unparent()
		self.password_text.unparent()

		super().do_dispose()

class GreetWidget(Gtk.Widget):
	__gsignals__: typing.ClassVar = {
		'poweroff': (GObject.SignalFlags.RUN_FIRST, None, ()),
		'restart': (GObject.SignalFlags.RUN_FIRST, None, ()),
		'sleep': (GObject.SignalFlags.RUN_FIRST, None, ()),
		'exit': (GObject.SignalFlags.RUN_FIRST, None, ()),
	}

	def __init__(self, work_dir: Path) -> None:
		super().__init__()

		layout = Gtk.CenterLayout()
		layout.set_orientation(Gtk.Orientation.VERTICAL)

		self.set_layout_manager(layout)

		passwd = Path("/etc/passwd").read_text().splitlines()

		users: list[str] = []

		for line in passwd:
			if "home" in line:
				users.append(line.split(":")[0])

		self.time = TimeDateWidget()
		self.time.set_parent(self)
		layout.set_start_widget(self.time)

		self.user_entry = UserEntryWidget(users[0])
		self.user_entry.set_parent(self)
		layout.set_center_widget(self.user_entry)

		self.power_control_box = PowerControlWidget(work_dir)
		self.power_control_box.set_parent(self)
		layout.set_end_widget(self.power_control_box)

		self.power_control_box.connect("poweroff", self.poweroff)
		self.power_control_box.connect("restart", self.restart)
		self.power_control_box.connect("sleep", self.sleep)
		self.power_control_box.connect("exit", self.exit)

		self.set_halign(Gtk.Align.CENTER)

	def poweroff(self, _) -> None:
		self.emit("poweroff")
	def restart(self, _) -> None:
		self.emit("restart")
	def sleep(self, _) -> None:
		self.emit("sleep")
	def exit(self, _) -> None:
		self.emit("exit")

	def do_dispose(self) -> None:
		self.time.unparent()
		self.user_entry.unparent()
		self.power_control_box.unparent()

		super().do_dispose()

class LoginManagerApp(Gtk.Application):
	def __init__(self, entries: list[tuple[str, str]], work_dir: Path):
		super().__init__(application_id="com.rdev.login-manager")

		self.entries = entries
		self.work_dir = work_dir

	def do_activate(self):
		window = Gtk.ApplicationWindow(application=self)

		window.set_title("Login Manager")

		window.set_default_size(850, 650)
		window.set_size_request(260, 320)

		window.set_decorated(False)

		provider = Gtk.CssProvider()
		provider.load_from_string(Path(self.work_dir / "style.css").read_text())

		Gtk.StyleContext.add_provider_for_display(
			Gdk.Display.get_default(),
			provider,
			Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
		)

		# box = GrubLoaderWidget(self.entries, self.work_dir)

		box = GreetWidget(self.work_dir)

		box.connect("poweroff", self.poweroff)
		box.connect("restart", self.restart)
		# box.connect("sleep", self.sleep)
		box.connect("exit", self.exit)

		overlay = Gtk.Overlay()

		bg = BlurredBackground("/home/rdev/wallpaper.png", 10)

		overlay.set_child(bg)
		overlay.add_overlay(box)

		window.set_child(overlay)

		window.present()

	def poweroff(self, _) -> None:
		run(["/usr/bin/env", "poweroff"], check=False) # TODO: выдавать ошибку

	def restart(self, _) -> None:
		run(["/usr/bin/env", "reboot"], check=False) # TODO: выдавать ошибку

	def exit(self, _) -> None:
		self.quit()

if __name__ == "__main__":
	file = Path("/boot/grub/grub.cfg").read_text()

	pattern = re.compile(r"^\s*menuentry\s+['\"](?P<title>[^'\"]+)['\"](?:\s+--class\s+(?P<class>[^\s'\"]+))?", re.MULTILINE | re.IGNORECASE)

	entries: list[tuple[str, str]] = []

	for match in pattern.finditer(file):
		title = match.group('title')

		os = str(match.group('class')).lower()

		if "uefi" in title.lower():
			os = "uefi"

		entries.append((title, os))

	app = LoginManagerApp(entries, Path(__file__).resolve().parent)

	app.run(None)
