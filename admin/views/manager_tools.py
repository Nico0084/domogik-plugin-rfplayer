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
