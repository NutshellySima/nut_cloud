import os
import subprocess
import datetime


def restarter(restarterabspath):
    Filepath=os.path.abspath(__file__)
    os.chdir(Filepath)
    subprocess.run(["git","pull"])
    restarter_file=os.path.join(restarterabspath,'log.txt')
    with open(restarter_file, "a+") as myfile:
        myfile.write(str(datetime.datetime.now()))