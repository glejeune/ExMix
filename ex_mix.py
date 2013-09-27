import sublime
import sublime_plugin
import subprocess
import os
import re
import threading
import glob


def settings():
    return sublime.load_settings('Ex Mix.sublime-settings')


class MixRunThread(threading.Thread):
    def __init__(self, env, path, cmd):
        self.env = env
        self.path = path
        self.cmd = cmd
        threading.Thread.__init__(self)

    def run(self):
        print(self.cmd)
        p = subprocess.Popen(
            self.cmd,
            env=self.env,
            cwd=self.path,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        for line in p.stdout.readlines():
            print(line)
        p.wait()
        print(self.cmd + ": ok!")


class MixPromptCommand(sublime_plugin.WindowCommand):

    def __init__(self, window):
        self.window = window

        self.with_args = False
        self.command = ""
        self.run_path = None

        custom_path = ":".join(settings().get("PATH"))
        self.os_env = os.environ.copy()
        my_path = ":".join([custom_path, self.os_env['PATH']])
        self.os_env['PATH'] = my_path

        self.mix_commands = []
        self.mix_commands_comment = ["something was wrong!"]

    def run(self, with_args):
        self.with_args = with_args
        self.mix_commands = []
        self.mix_commands_comment = []
        self.run_path = self.mix_directory()

        if self.run_path is None:
            sublime.error_message("Can't find mix file")
            return

        sublime.status_message("Run mix in " + self.run_path)
        p = subprocess.Popen(
            'mix help',
            env=self.os_env,
            cwd=self.run_path,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        for line in p.stdout.readlines():
            pattern = re.compile("^\s*mix\s*([^\s]*)\s*#\s*(.*)$")
            match = pattern.match(line)
            if match:
                self.mix_commands.append(match.group(1))
                self.mix_commands_comment.append(
                    match.group(1) + " : " + match.group(2)
                )
        p.wait()
        self.window.show_quick_panel(
            self.mix_commands_comment,
            self.on_done,
            sublime.MONOSPACE_FONT
        )

    def on_done(self, arg):
        if arg >= 0:
            self.command = "mix " + self.mix_commands[arg]
            if self.with_args:
                self.window.show_input_panel(
                    "Arguments for " + self.command,
                    "", self.run_mix, None, None
                )
            else:
                self.run_mix("")

    def run_mix(self, args=""):
        MixRunThread(
            self.os_env,
            self.run_path,
            self.command + " " + args
        ).start()

    def mix_directory(self):
        file_name = self.window.active_view().file_name()
        if file_name is None:
            file_name = self.window.folders()
            print(str(file_name))
            if len(file_name) != 1:
                return None
            else:
                return self.get_mix_directory(file_name[0])
        else:
            path = file_name.split("/")
            path.pop()
            path = "/".join(path)
            return self.get_mix_directory(path)

    def get_mix_directory(self, path):
        print("looking for mix in " + path)
        if(len(glob.glob(os.path.join(path, "mix.*"))) == 0):
            if(path != "/"):
                return self.get_mix_directory(
                    os.path.realpath(os.path.join(path, '..'))
                )
            else:
                return None
        else:
            return path
