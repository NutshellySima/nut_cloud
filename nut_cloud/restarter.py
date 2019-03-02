import os
import subprocess
import datetime
import hmac
from hashlib import sha1

def verifyrestart(body,key,hashval):
    verifier=hmac.new(key, body, sha1)
    digest='sha1=' + verifier.hexdigest()
    if hmac.compare_digest(digest,hashval):
        return True
    else:
        return False

def restarter(restarterabspath):
    Filepath=os.path.abspath(__file__)
    os.chdir(os.path.abspath(os.path.join(Filepath,'../')))
    subprocess.run(["git","pull"])
    restarter_file=os.path.join(restarterabspath,'log.txt')
    with open(restarter_file, "a+") as myfile:
        myfile.write(str(datetime.datetime.now())+'\n')