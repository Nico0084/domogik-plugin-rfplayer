# -*- coding: utf-8 -*-
from domogik.admin.application import app
from domogik.common.utils import get_sanitized_hostname

from domogikmq.reqrep.client import MQSyncReq
from domogikmq.message import MQMessage

def get_manager_status(abort = False):
    data = {u'status': u'dead', u'rfPlayers': [], u'error': u''}
    if not abort :
        cli = MQSyncReq(app.zmq_context )
        msg = MQMessage()
        msg.set_action('rfplayer.manager.getstatus')
        res = cli.request('plugin-rfplayer.{0}'.format(get_sanitized_hostname()), msg.get(), timeout=10)
        if res is not None:
            data = res.get_data()
        else : data['error'] =  u'Plugin timeout response.'
    return data



def get_openzwave_info(abort = False):
    data = {u'status': u'dead', u'PYOZWLibVers':u'unknown', u'ConfigPath': u'undefined', 'uUserPath': u'not init',
                u'Options' : {},
                u'error': u''}
    if not abort :
        cli = MQSyncReq(app.zmq_context)
        msg = MQMessage()
        msg.set_action('ozwave.openzwave.get')
        res = cli.request('plugin-ozwave.{0}'.format(get_sanitized_hostname()), msg.get(), timeout=10)
        if res is not None:
            data = res.get_data()
        else : data['error'] =  u'Plugin timeout response.'
    return data
def get_controller_state(NetworkID, abort = False):
    data = {u'NetworkID': u'unknown', u'Node': 1, u'Init_state': u'unknown', u'Node count': 0, u'Protocol': u'unknown',
                u'Node sleeping': 0, u'ListNodeId': [], u'Library': u'undefined', u'state': u'dead', u'Version': u'undefined',
                u'HomeID': u'undefined', u'Primary controller': u'undefined', u'Model': u'undefined', u'Poll interval': 0,
                u'error': u''}
    if not abort :
        cli = MQSyncReq(app.zmq_context)
        msg = MQMessage()
        msg.set_action('ozwave.ctrl.get')
        msg.add_data('NetworkID', NetworkID)
        res = cli.request('plugin-ozwave.{0}'.format(get_sanitized_hostname()), msg.get(), timeout=10)
        if res is not None:
            data = res.get_data()
        else : data['error'] =  u'Plugin timeout response.'
    return data

def get_controller_nodes(NetworkID, abort = False):
    data = { u'nodes': [],
                u'error': u''}
    if not abort :
        cli = MQSyncReq(app.zmq_context)
        msg = MQMessage()
        msg.set_action('ozwave.ctrl.nodes')
        msg.add_data('NetworkID', NetworkID)
        res = cli.request('plugin-ozwave.{0}'.format(get_sanitized_hostname()), msg.get(), timeout=10)
        if res is not None:
            data = res.get_data()
        else : data['error'] =  u'Plugin timeout response.'
    return data

def get_openzwave_all_products(abort = False):
    data = {u'data': [], u'error': u''}
    if not abort :
        cli = MQSyncReq(app.zmq_context)
        msg = MQMessage()
        msg.set_action('ozwave.openzwave.getallproducts')
        res = cli.request('plugin-ozwave.{0}'.format(get_sanitized_hostname()), msg.get(), timeout=10)
        if res is not None:
            data = res.get_data()
        else : data['error'] =  u'Plugin timeout response.'
    return data

def get_request(client_id, action, data, abort = False):
    resData = {u'error': u'', u'data': {}}
    if not abort :
        cli = MQSyncReq(app.zmq_context)
        msg = MQMessage()
        msg.set_action(action)
        for key in data:
            msg.add_data(key, data[key])
        res = cli.request(client_id, msg.get(), timeout=10)
        if res is not None:
            resData = res.get_data()
            action = res.get_action()
        else : resData['error'] =  u'Plugin timeout response on request : {0}.'.format(action)
    return action, resData
