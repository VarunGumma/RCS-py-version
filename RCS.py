import sys
from os import listdir
from hashlib import sha256
from getpass import getpass
from pickle import load, dump
from time import time, strftime, localtime
from subprocess import run, TimeoutExpired
from os.path import exists, splitext, join, abspath


class Testcase:

    def __init__(self, idx, inp, out, ans, judged_at, runtime, status, remark):
        self._idx = idx
        self._status = status
        self._remark = remark
        self._judged_at = judged_at
        self._input = inp.decode()
        self._output = out.decode()
        self._answer = ans.decode()
        self._runtime = str(runtime)[:5]
        if len(self._runtime) < 5:
            self._runtime += '0'

    def display(self):
        print("| {:^4} | {:^30} | {:^3} ms | {}".format(
            self._idx,
            self._status,
            self._runtime,
            self._remark
        ),
            end="\r\n"
        )

    def reveal(self):
        compress = (lambda x: (x[:255] + ["", "..."][len(x) > 255]))
        print("\nTESTCASE #{}".format(self._idx))
        print("VERDICT: {}".format(self._status))
        print("RUNTIME: {} ms".format(self._runtime))
        print("JUDGED AT: {}".format(self._judged_at))
        print("\nINPUT:\n{}".format(compress(self._input)))
        print("\nOUTPUT:\n{}".format(compress(self._output)))
        print("\nJURY'S OUTPUT:\n{}".format(compress(self._answer)))
        print("\nRemark:\n{}".format(self._remark))


class Checker:

    def __init__(self, base_path):
        self._TIMELIMIT = 2000
        self._INBUILT_PASS = "1a79668eac4051a9128b81c116007d1b41ce17828d7722afc9746699f4e817b8"

        self._COMPILE_CMDS = {
            ".c": "gcc {} -o {} --std=c99 -lm",
            ".cpp": "g++ {} -o {} --std=c++17"
        }

        self._VERDICT_MAP = {
            1: self._ansi_color(32, "ACCEPTED"),
            2: self._ansi_color(31, "WRONG_ANSWER"),
            3: self._ansi_color(33, "TIME_LIMIT_EXCEEDED"),
            4: self._ansi_color(31, "RUNTIME_ERROR")
        }

        self._BASE_PATH = base_path
        if sys.argv[1] == "judge":
            if len(sys.argv) < 3:
                print("Usage: RCS.py judge X.c")
                sys.exit(0)
            if not exists(sys.argv[2]):
                print("Specified file doesn't exist")
            else:
                self._verify_password()
                self._judge(sys.argv[2])
        elif sys.argv[1] == "reveal":
            if len(sys.argv) < 3:
                print("usage: RCS.py reveal X")
                sys.exit(0)
            try:
                self._verify_password()
                with open("results.dat", "rb") as results_file:
                    pack = load(results_file)
                    results_file.close()
            except FileNotFoundError:
                print("Judge atleast once before revealing")
                sys.exit(0)
            pack[int(sys.argv[2])].reveal()
        elif sys.argv[1] == "clean":
            run("rm results.dat")
            run("rm RCS.exe")
        else:
            print("Usage: RCS.py judge X.c | reveal X | clean")

    def _read(self, fname):
        path_to_file = join(self._BASE_PATH, fname)
        with open(path_to_file, "rb") as input_file:
            req_input = input_file.read()
            input_file.close()
        return req_input

    def _ansi_color(self, fgd, text):
        return "\033[1;{}m{}\033[0m".format(fgd, text)

    def _verify_password(self):
        tries = 3
        while tries > 0:
            if self._INBUILT_PASS == sha256(getpass("enter passwd: ").encode()).hexdigest():
                return
            else:
                print("Incorrect password. [{} tr{} left]".format(tries-1, ["ies", "y"][tries == 2]))
            tries -= 1
        print("Three incorrect attempts detected. Please verify password and try again.")
        sys.exit(0)

    def _judge(self, fname):
        pack = []
        score = verdict = 0
        judged_at = remark = None
        stem, ext = splitext(fname)
        if ext not in self._COMPILE_CMDS:
            print("{} extension is not allowed.\nAvailable languages: C, C++".format(ext))
            sys.exit(0)
        testcases = max_score = len(listdir(join(self._BASE_PATH, "inputs")))
        command = self._COMPILE_CMDS[ext].format(fname, stem)
        process = run(command)

        if not process.returncode:
            for tno in range(testcases):
                try:
                    req_input = self._read(
                        "inputs/inp{}.txt".format(tno+1)).strip()
                    req_output = self._read(
                        "outputs/out{}.txt".format(tno+1)).strip()
                    start, end = time(), None
                    process = run("./{}".format(stem),
                                  input=req_input,
                                  capture_output=True,
                                  timeout=self._TIMELIMIT/1000)
                    end = time()
                    if not process.returncode:
                        output = process.stdout.strip()
                        diff = (req_output == output)
                        verdict = (1 if diff else 2)
                        remark = ("OK" if diff else "WA")
                        score += int(diff)
                    else:
                        remark = "RTE"
                        verdict = 4
                except TimeoutExpired:
                    if end is None:
                        end = time()
                    output = b"<no output>"
                    verdict = 3
                    remark = "TLE"
                except FileNotFoundError:
                    print("unable to fetch necessary files")
                    sys.exit(0)
                finally:
                    judged_at = strftime('%I:%M:%S %p, %d-%b-%Y', localtime())

                runtime = round((end - start), 4)
                status = self._VERDICT_MAP[verdict]
                test = Testcase(idx=tno,
                                inp=req_input,
                                out=output,
                                ans=req_output,
                                judged_at=judged_at,
                                runtime=runtime,
                                status=status,
                                remark=remark)

                if not tno:
                    print("\n+{}+".format('-'*39))
                    print("| {:^4} | {:^19} | {:^4}  | ".format("SNO", "VERDICT", "RUNTIME"))
                    print("+{}+".format('-'*39))
                    print("+{}+".format('-'*39))
                test.display()
                print("+{}+".format('-'*39))
                pack.append(test)

            with open("results.dat", "wb") as results_file:
                dump(pack, results_file)
                results_file.close()
            
            print("\t+{}+".format('-'*23))
            print("\t| {:^21} |".format("SCORE: {}/{}".format(score, max_score)))
            print("\t+{}+".format('-'*23))
            if not score:
                print("\t| {:^21} |".format(self._ansi_color(31, "BETTER LUCK NEXT TIME")))
                print("\t+{}+".format('-'*23))
            elif score == max_score:
                print("\t| {:^32} |".format(self._ansi_color(32, "WELL DONE")))
                print("\t+{}+".format('-'*23))
        else:
            print(self._ansi_color(31, "COMPILATION_ERROR"))


# main function
def main():
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = abspath(".")
    Checker(base_path=base_path)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nQuitting Judge...\n")
