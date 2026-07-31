#!/usr/bin/env python3.14

import re

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gtk, Gdk, GLib, Graphene

from pathlib import Path

import time

from subprocess import run

import sys

def boot(_, index) -> None:
	run(["/usr/bin/env", "sh", "-c", f"grub-reboot {index} && reboot"], check=False) # TODO: выдавать ошибку

def poweroff(_) -> None:
	run(["/usr/bin/env", "poweroff"], check=False) # TODO: выдавать ошибку

def restart(_) -> None:
	run(["/usr/bin/env", "reboot"], check=False) # TODO: выдавать ошибку

def quit(_) -> None:
	sys.exit(0)

def new_power_button(image_path: str, name: str="", tooltip_text: str="", pixel_size: int=24) -> Gtk.Button:
	power_button = Gtk.Button(name=name, tooltip_text=tooltip_text)
	power_button.add_css_class("button")
	power_texture = Gdk.Texture.new_from_filename(image_path)
	power_image = Gtk.Image.new_from_paintable(power_texture)
	power_image.set_pixel_size(pixel_size)
	power_image.set_name("power-image")
	power_image.add_css_class("image")
	power_button.set_child(power_image)

	return power_button

def place_power_control(work_dir: Path) -> tuple[Gtk.Button, Gtk.Button, Gtk.Button, Gtk.Button]:
	power_button = new_power_button(str(work_dir / "icons/power.svg"), name="power-button", tooltip_text="Выключить компьютер")
	power_button.connect("clicked", poweroff)

	restart_button = new_power_button(str(work_dir / "icons/restart.svg"), name="restart-button", tooltip_text="Перезагрузить компьютер")
	restart_button.connect("clicked", restart)

	sleep_button = new_power_button(str(work_dir / "icons/sleep.svg"), name="sleep-button", tooltip_text="Спящий режим")

	exit_button = new_power_button(str(work_dir / "icons/exit.svg"), name="exit-button", tooltip_text="Выйти из сессии", pixel_size=28)
	exit_button.connect("clicked", quit)

	return (power_button, restart_button, sleep_button, exit_button)

def grub_load_scene(entries: list[tuple[str, str]], work_dir: Path, box: Gtk.Box) -> None:
	text = Gtk.Label(label="Выберите OS для загрузки:", name="title")
	text.set_halign(Gtk.Align.CENTER)
	box.append(text)

	scrollable = Gtk.ScrolledWindow()
	scrollable.set_vexpand(True)
	scrollable.set_margin_bottom(20)
	scrollable.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
	scrollable.set_overlay_scrolling(False)

	entries_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

	scrollable.set_child(entries_box)

	for i, entry in enumerate(entries):
		button = Gtk.Button()

		center_box = Gtk.CenterBox()

		path = str(work_dir / f"icons/{entry[1]}.svg")

		if not Path(path).exists():
			path = str(work_dir / "icons/question.svg")

		texture = Gdk.Texture.new_from_filename(path)

		image = Gtk.Image.new_from_paintable(texture)

		image.add_css_class("entry_icon")

		image.set_pixel_size(64)

		left_label = Gtk.Label(label=entry[0])
		left_label.set_halign(Gtk.Align.START)

		center_box.set_start_widget(image)
		center_box.set_center_widget(left_label)

		button.add_css_class("entry")

		button.set_child(center_box)

		button.connect("clicked", boot, i)

		entries_box.append(button)

	box.append(scrollable)

	power_control_box = Gtk.Box(name="power-control-box")

	power_button, restart_button, sleep_button, exit_button = place_power_control(work_dir)

	power_control_box.append(power_button)
	power_control_box.append(restart_button)
	power_control_box.append(sleep_button)
	power_control_box.append(exit_button)

	power_control_box.set_halign(Gtk.Align.START)

	box.append(power_control_box)

def update_time(time_label: Gtk.Label, date_label: Gtk.Label) -> bool:
	time_label.set_label(time.strftime("%H:%M"))
	date_label.set_label(time.strftime("%d %B, %Y"))

	return True

def greet_scene(work_dir: Path, box: Gtk.Box) -> None:
	passwd = Path("/etc/passwd").read_text().splitlines()

	users: list[str] = []

	for line in passwd:
		if "home" in line:
			users.append(line.split(":")[0])

	form = Gtk.CenterBox(orientation=Gtk.Orientation.VERTICAL)
	form.set_vexpand(True)

	time_form_center = Gtk.CenterBox(orientation=Gtk.Orientation.VERTICAL)
	time_form_center.set_vexpand(True)

	time_form = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

	time_label = Gtk.Label(name="time-label")
	time_form.append(time_label)

	date_label = Gtk.Label(name="date-label")
	time_form.append(date_label)

	update_time(time_label, date_label)

	time_form_center.set_center_widget(time_form)

	form.set_start_widget(time_form_center)

	user_password_input = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

	user_label = Gtk.Label(label=users[0])
	user_label.add_css_class("active-user-label")
	user_password_input.append(user_label)

	password_text = Gtk.PasswordEntry(name="password-text", placeholder_text="Введите пароль")
	user_password_box = Gtk.CenterBox(orientation=Gtk.Orientation.HORIZONTAL, center_widget=password_text)
	user_password_input.append(user_password_box)

	form.set_center_widget(user_password_input)

	power_control_box = Gtk.Box(name="power-control-box")

	buttons = place_power_control(work_dir)

	for button in buttons:
		power_control_box.append(button)

	power_control_box.set_halign(Gtk.Align.START)

	form.set_end_widget(power_control_box)

	box.append(form)

	GLib.timeout_add(1000, update_time, time_label, date_label)

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

class LoginManagerApp(Gtk.Application):
	def __init__(self, entries: list[tuple[str, str]], work_dir: Path):
		super().__init__(application_id="com.rdev.login-manager")

		self.entries = entries
		self.work_dir = work_dir

	def do_activate(self):
		window = Gtk.ApplicationWindow(application=self)

		window.set_title("Login Manager")

		window.set_default_size(850, 650)

		window.set_decorated(False)

		provider = Gtk.CssProvider()
		provider.load_from_string(Path(self.work_dir / "style.css").read_text())

		Gtk.StyleContext.add_provider_for_display(
			Gdk.Display.get_default(),
			provider,
			Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
		)

		box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

		# grub_load_scene(self.entries, self.work_dir, box)

		greet_scene(self.work_dir, box)

		overlay = Gtk.Overlay()

		bg = BlurredBackground("/home/rdev/wallpaper.png", 10)

		overlay.set_child(bg)

		overlay.add_overlay(box)

		window.set_child(overlay)

		window.present()

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
