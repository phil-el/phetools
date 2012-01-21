#!/usr/bin/python
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 2 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#
#
#    copyright thomasv1 at gmx dot de


# todo : use urllib2


__module_name__ = "wikisourceocr"
__module_version__ = "1.0"
__module_description__ = "wikisource ocr bot"



import sys,os
import socket
import string
import re, Queue
import sre_constants
import thread, time
import simplejson
import urllib2

task_queue = []
#task_queue = Queue.Queue(0)


tesseract_languages = { 
	'fr':"fra",
        'en':"eng",
        'de':"deu",
        'de-f':"deu-f",
        'la':"ita",
        'it':"ita",
	'es':"spa",
	'pt':"spa" }



def bot_listening():

    sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)
    try:
        sock.bind(('',12345))
    except:
        print "could not start listener : socket already in use"
        thread.interrupt_main()
        return

    print date_s(time.time())+ " START"
    sock.listen(1)

    # wait for requests
    try:
        while True:
            conn, addr = sock.accept()
            data = conn.recv(1024)
            try:
	        url,lang,user = eval(data)
	    except:
		print "error",data
		conn.close()
		continue

	    t = time.time()
	    user = user.replace(' ','_')

	    if url=="status":
		#print date_s(t) +" STATUS"
		conn.send("OCR daemon is running. %d jobs in queue.<br/><hr/>"%len(task_queue))
		for i in task_queue:
		    conn.send( date_s(i[3])+' '+i[2]+" "+i[1]+" "+i[0].split('/')[-1]+"<br/>")
		conn.close()
		continue

	    print date_s(t)+" REQUEST "+user+' '+lang+' '+url.split('/')[-1]
	    task_queue.insert(0,(url,lang,user,t,conn))

    finally:
	sock.close()



def date_s(at):
    t = time.gmtime(at)
    return "[%02d/%02d/%d:%02d:%02d:%02d]"%(t[2],t[1],t[0],t[3],t[4],t[5])


def ocr_image(url,codelang):

    try:
	lang = tesseract_languages[codelang]
    except:
        lang = "eng"

    os.system("rm -f image2.*")

    f = "image2.jpg"

    #url = url.replace("1024px","2900px")
    os.system("wget -q -O %s \"%s\""%(f,url))
    if not os.path.exists(f):
	print "could not download url"
	return ""

    os.system("nice -n 19 convert -normalize image2.jpg image2.png")
    os.system("nice -n 19 convert -monochrome image2.png image2.tif")
    os.system("nice -n 19 tesseract image2.tif image2 -l %s 2>tesseract_err"%lang)

    try:
        file = open("image2.txt")
	txt = file.read()
	file.close()
    except:
	return ""


    try:
        return simplejson.dumps(txt)
    except:
        return ""



def main():
    thread.start_new_thread(bot_listening,())
    while 1:

        if task_queue != []:
            url,lang,user, t, conn = task_queue[-1]
        else:
	    try:
	        time.sleep(0.5)
	    except:
		break
            continue
	    
	time1 = time.time()
	out = ocr_image(url,lang)
        conn.send(out)
	conn.close()
	time2 = time.time()
	if out:
	    res = " DONE    "
	else:
	    res = " FAILED  "
	print date_s(time2)+res+user+" "+lang+" %s (%.2f)"%(url.split('/')[-1],time2-time1)
	task_queue.pop()




if __name__ == "__main__":

    main()
