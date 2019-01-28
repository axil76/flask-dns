#!/usr/bin/env python2.7

from flask import Flask, abort, redirect, request 
from flask_sslify import SSLify
from flask import request
from flask_restful import reqparse, abort, Resource, Api
import ConfigParser
import subprocess, json
import pdb
import sys, os, time, atexit
import logging
import daemon
import ssl
import argparse
from signal import SIGTERM
from pydaemon import Daemon
#from daemonize import Daemonize
from time import sleep
#from updatedns import DnsUpdate

#try:
from updatedns.updatedns import DnsUpdate
#except ImportError:
    #print('Error load library updatedns ')

#import updatedns

global Verbose
Verbose = False
global standardexit
standardexit={}  
global options 
options = {}


PARSER = argparse.ArgumentParser(description='config file')
PARSER.add_argument("-c", "--config", type=str,
                    help='File config',
                    default="config.ini")
PARSER.add_argument("-a", "--action", type=str,
                    help='start/stop/debug/reload/status Flask DNS')
ARGS = PARSER.parse_args()

app = Flask(__name__)
api = Api(app)

def launchscript(script):
    # pdb.set_trace()
    process = subprocess.Popen(script, shell=True, stdout=subprocess.PIPE)
    stdoutdata, stderrdata = process.communicate()
    return stdoutdata.rstrip()
    
# Uncomment those line if you want to run Flask Without @api.resource Decorator  
# api.add_resource(DnsZonesRecordsList, '/dns/zones/<string:zonename>/records')
# api.add_resource(DnsZonesRecords, '/dns/zones/<string:zonename>/records/<string:subdomain>')

def loadImports(path):
    files = os.listdir(path)
    imps = []
    for i in range(len(files)):
        name = files[i].split('.')
        if len(name) > 1:
            if name[1] == 'py' and name[0] != '__init__':
               name = name[0]
               imps.append(name)

    file = open(path+'__init__.py','w')
    toWrite = '__all__ = '+str(imps)
    file.write(toWrite)
    file.close()


def json_message_list(status,message):
    #message.rstrip('\n')
    message = message[:-1]
    content = '{"status" :"'+status+'","message":['+ message +']'    
    return content


def parse_config(config):
    """
    Parse the user config and retreieve the nameserver, port
    """
    #options = {}
    parser = ConfigParser.ConfigParser()
    parser.read(config)
    options['path'] = parser.get('flask-dns', 'path')
    options['version'] = parser.get('flask-dns', 'version')
    options['nameserver'] = parser.get('nameserver', 'server')
    options['port'] = parser.get('nameserver', 'port')
    options['usessl'] = parser.get('nameserver', 'usessl')
    options['sslcrt'] = parser.get('nameserver', 'sslcrt')
    options['sslkey'] = parser.get('nameserver', 'sslkey')
    options['debug'] = parser.get('nameserver', 'debug')     
    options['log'] = parser.get('file', 'log')
    options['pid'] = parser.get('file', 'pid') 
    return options


def parse_config_dns(section,key):
    """
    Parse the user config and retreieve the nameserver, port for DNS
    """    
    parser = ConfigParser.ConfigParser()
    logging.info('Config file : ' + init + '-' + section + '-' + key )
    parser.read(init)
    value = parser.get(section, key)     
    return value


class flask_dns_daemon(Daemon): 
    def run(self): 
       try:
        logging.info('Start flash-dns with '+ config['nameserver'] + ' and port ' + config['port'] + ' ')        
        #app.run(host=SERVER,port=PORT,debug=True)
        #Config ssl 
        if config['usessl'] == "no":
         logging.info('no ssl activated')
         #app.run(host=SERVER,port=PORT,debug=True)         
         app.run(host=SERVER,port=PORT)
        else:
         logging.info('ssl activated')        
         ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)    
         ssl_context.load_cert_chain(SSLCRT, SSLKEY)
         #app.run(host=SERVER,port=PORT,ssl_context=context,debug=True)         
         app.run(host=SERVER,port=PORT,ssl_context=context)        
       except Exception, e:
		logging.exception('Error to start flask-dns')
       while True:
        time.sleep(5)	   
 
 
class DnsZonesRecordsList(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('subdomain', type = str, required = True, help = 'No subdomain provided', location = 'json')
        self.reqparse.add_argument('value', type = str, required = True, default = "", location = 'json') 
        self.reqparse.add_argument('type', type = str, required = False, default = "A", location = 'json')   
        self.reqparse.add_argument('ttl', type = int, required = False, default = "300", location = 'json')
        self.reqparse.add_argument('ptr', type = str, required = True, default = "", location = 'json')   
        super(DnsZonesRecordsList, self).__init__()
  
    def post(self, zonename):

        DNS = DnsUpdate()
        args = self.reqparse.parse_args()
        # print args
        #fqdn = args['subdomain']+zonename
        fqdn = zonename

        if args['ttl'] != "":
            ttl="-t "+str(args['ttl'])
            ttl=str(args['ttl'])
        else:
            ttl=""
        myInput=[]
        myInput.append('add')
        myInput.append(args['subdomain'] + '.' + zonename)
        myInput.append(args['type'])
        myInput.append(args['value']) 
              
        server=''
        key=''
        user=''
        # Load config DNS
        logging.info('POST get zone config ... ') 
        if "spia." in zonename:
            server = parse_config_dns('dns-trz', 'server') 
            key = parse_config_dns('dns-trz', 'keyfile')
            user = parse_config_dns('dns-trz', 'user')
        elif "spid." in zonename: 
            server = parse_config_dns('dns-sto', 'server') 
            key = parse_config_dns('dns-sto', 'keyfile')
            user = parse_config_dns('dns-sto', 'user')  
        elif "bind." in zonename:
            server = parse_config_dns('dns-qualif', 'server') 
            key = parse_config_dns('dns-qualif', 'keyfile')
            user = parse_config_dns('dns-qualif', 'user') 
        elif "bind2." in zonename: 
            server = parse_config_dns('dns-qualif2', 'server') 
            key = parse_config_dns('dns-qualif2', 'keyfile')
            user = parse_config_dns('dns-qualif2', 'user') 
        elif "qualif" in zonename: 
            server = parse_config_dns('dns-qualif', 'server') 
            key = parse_config_dns('dns-qualif', 'keyfile')
            user = parse_config_dns('dns-qualif', 'user') 

        logging.info('POST end zone config ... ')  

        logging.info('Request Add')
        logging.info(myInput)
        
        #Function doUpdate(Server, KeyFile, Origin, TimeToLive, doPTR, myInput)
        #dnsupdate -s server -k key -t ttl add _minecraft._tcp.mc.example.com SRV 0 0 25566 mc.example.com
        #DNS.doUpdate(Server, Key, Origin,TimeToLive, doPTR, myInput) 

        if "True" in args['ptr']:
            doPTR = True
            logging.info('PTR yes')
        else:
            doPTR = False
            logging.info('PTR no') 

        result = DNS.doUpdate(server, key, fqdn, ttl, doPTR, myInput, user)

        #DNS.doUpdate(self,server, key, fqdn, ttl,False, myInput) 
        logging.info('End Add')   
        msg = json.loads(result)        
        # result = launchscript('/root/iac-dns/scripts/dnsupdate.py -v -s 203.45.130.52 -k Kpaas_key.+157+01647.private  {1} -x add {0} IN {2} {3}'.format(fqdn,ttl,type,value))
        # result = {'message':'OK','fqdn':args['fqdn'],'@IP':args['value'] }
        status_code = msg['status']
        del msg['status']
        #print result
        return result, status_code
        
        
# @api.resource('/dns/zones/<string:zonename>/records/<string:subdomain>')
class DnsZonesRecords(Resource):
    def __init__(self):
        self.reqparse = reqparse.RequestParser()
        self.reqparse.add_argument('subdomain', type = str, required = True, help = 'No subdomain provided', location = 'json')
        self.reqparse.add_argument('value', type = str, required = True, default = "", location = 'json') 
        self.reqparse.add_argument('type', type = str, required = False, default = "A", location = 'json')   
        self.reqparse.add_argument('ttl', type = int, required = False, default = "300", location = 'json')
        self.reqparse.add_argument('ptr', type = str, required = True, default = "", location = 'json')   
        super(DnsZonesRecords, self).__init__()
        
    def delete(self, zonename, subdomain):
        # pdb.set_trace()
        DNS = DnsUpdate()
        args = self.reqparse.parse_args()
        # print args
        #fqdn = args['subdomain']+zonename
        fqdn = zonename
        if args['ttl'] != "":
            ttl="-t "+str(args['ttl'])
        else:
            ttl=""
        myInput=[]
        myInput.append('del')   
        
        if "CNAME" in args['type']:
            myInput.append(args['subdomain'])
            #myInput.append(args['subdomain']+ '.' + zonename)
        elif "A" in args['type']:  
            myInput.append(args['subdomain']+ '.' + zonename)    
        elif "AAAA" in args['type']:    
            myInput.append(args['subdomain']+ '.' + zonename)

        myInput.append(args['type'])
        myInput.append(args['value'])
        #debug
        #print (myInput)
        server=''
        key=''
        user=''
        logging.info('DEL get zone config ... ') 
        # Load config DNS        
        if "spia." in zonename:
            server = parse_config_dns('dns-trz', 'server') 
            key = parse_config_dns('dns-trz', 'keyfile')
            user = parse_config_dns('dns-trz', 'user')
        elif "spid." in zonename: 
            server = parse_config_dns('dns-sto', 'server') 
            key = parse_config_dns('dns-sto', 'keyfile')
            user = parse_config_dns('dns-sto', 'user') 
        elif "bind." in zonename:
            server = parse_config_dns('dns-qualif', 'server') 
            key = parse_config_dns('dns-qualif', 'keyfile')
            user = parse_config_dns('dns-qualif', 'user')
        elif "bind2." in zonename: 
            server = parse_config_dns('dns-qualif2', 'server') 
            key = parse_config_dns('dns-qualif2', 'keyfile')
            user = parse_config_dns('dns-qualif2', 'user')
        elif "qualif" in zonename: 
           server = parse_config_dns('dns-qualif', 'server') 
           key = parse_config_dns('dns-qualif', 'keyfile')
           user = parse_config_dns('dns-qualif', 'user')            
        
        logging.info('DEL end zone config ... ')

        logging.info('Request Delete')
        logging.info(myInput)        
        #Function doUpdate(Server, KeyFile, Origin, TimeToLive, doPTR, myInput)            
        if "True" in args['ptr']:
            doPTR = True
            logging.info('PTR yes')
        else:
            doPTR = False
            logging.info('PTR no')     
                
        result = DNS.doUpdate(server, key, fqdn, ttl, doPTR, myInput, user)
        logging.info('End delete')
        msg = json.loads(result) 
        #print (msg)
        #result = json.loads(launchscript(PATH+'/scripts/dnsupdate.py -s '+config['dns']+' -k '+PATH+config['key']+' {1} -x del {0} IN {2} {3}'.format(fqdn,ttl,type,value)))
        # result = launchscript('/root/iac-dns/scripts/dnsupdate.py -s 203.45.130.52 -k Kpaas_key.+157+01647.private  {1} -x del {0} IN {2} {3}'.format(fqdn,ttl,type,value))
        status_code = msg['status']
        del msg['status']
        return result, status_code

    def put(self, zonename, subdomain):
        args = self.reqparse.parse_args()
        #print args
        fqdn = args['subdomain']+zonename
        if args['ttl'] != "":
            ttl="-t "+str(args['ttl'])
        else:
            ttl=""
        type=args['type']
        value=args['value']
        result = json.loads(launchscript(PATH+'/scripts/dnsupdate.py -s 203.45.130.52 -k Kpaas_key.+157+01647.private  {1} -x update {0} IN {2} {3}'.format(fqdn,ttl,type,value)))
        del result['status']
        return result, status_code

# Uncomment those line if you want to run Flask Without @api.resource Decorator  
api.add_resource(DnsZonesRecordsList, '/dns/zones/<string:zonename>/records')
api.add_resource(DnsZonesRecords, '/dns/zones/<string:zonename>/records/<string:subdomain>')


if __name__ == '__main__':

    #Load config file
    current = os.getcwd()
    #loadImports(current + '/dns/')    
    #Parse argument
    if ARGS.config:        
        init = current + '/' + ARGS.config        
    else:
        myname=os.path.basename(sys.argv[0])
        #current = os.getcwd()
        init = os.path.abspath('.')+'./config.ini' 

    #Parse config file
    config = parse_config(init)
    LOGFILE = config['log']
    PIDFILE = config['pid']
    PATH = config['path']
    SSLCRT = config['sslcrt']
    SSLKEY = config['sslkey']
    PORT=int(config['port'])
    SERVER=config['nameserver']
    
    logging.basicConfig(filename=LOGFILE,level=logging.DEBUG) 

    #Config log to debug
        #Config log to debug
    if config['usessl'] == "no":
      logging.info('Start daemon no ssl ')  
      daemon = flask_dns_daemon(PIDFILE)
    else:
      logging.info('Start daemon with ssl ')    
      daemon = flask_dns_daemon(PIDFILE,SSLCRT,SSLKEY)
     
    #if len(ARGS.action) == 2:
    if ARGS.action:
     if 'start' == ARGS.action:
       try:
         logging.info('Started')  
         daemon.start()
       except:
         pass
     
     elif 'stop' == ARGS.action:
      logging.info('Stop daemon')     
      print "Stopping ..."
      daemon.stop()
      
     elif 'debug' == ARGS.action:
      print "Start in debug mode  ..."
      app.run(host=SERVER,port=PORT,debug=config['debug'])
      
     elif 'restart' == ARGS.action:
      logging.info('Restart daemon')   
      print "Restarting ..."
      daemon.restart()
              
     elif 'status' == ARGS.action:
      try:
       pf = file(PIDFILE,'r')
       pid = int(pf.read().strip())
       pf.close()
      except IOError:
       pid = None
      except SystemExit:
       pid = None
      
      if pid:
       print 'flask-dsl is running as pid %s' % pid
      else:
       print 'flask-dsl is not running.'
      
     else:
       print "Unknown command"
       sys.exit(2)
       sys.exit(0)
    else:
     print "usage: %s -a start|stop|restart|status -c file " % sys.argv[0]
     sys.exit(2)

 
    #daemon = Daemonize(app=myname, pid=pidfile, action=main)
    #daemon.start()
    
