# -*- coding: utf-8 -*-

### common imports
from flask import Blueprint, jsonify, request
from domogik.common.utils import get_packages_directory
from domogik.admin.application import render_template
from domogik.admin.views.clients import get_client_detail
from jinja2 import TemplateNotFound

### package specific imports
from domogik_packages.plugin_rfplayer.admin.views.manager_tools import get_manager_status, get_openzwave_info, \
                                                                     get_controller_state, get_controller_nodes, get_request, \
                                                                     get_openzwave_all_products

### common tasks
package = "plugin_rfplayer"
template_dir = "{0}/{1}/admin/templates".format(get_packages_directory(), package)
static_dir = "{0}/{1}/admin/static".format(get_packages_directory(), package)

plugin_rfplayer_adm = Blueprint(package, __name__,
                        template_folder = template_dir,
                        static_folder = static_dir)

### package specific functions

@plugin_rfplayer_adm.route('/<client_id>')
def index(client_id):
    detail = get_client_detail(client_id)
    abort = False
#    if detail["status"] not in ["alive",  "starting"] : abort = True
#    openzwaveInfo = get_openzwave_info(abort)
#    if openzwaveInfo['error'] == 'Plugin timeout response.': abort = True
    manager = get_manager_status(abort)
#    if rfP_List['error'] == 'Plugin timeout response.': abort = True
    print(u"Acces page...")
    try:
        #return render_template('{0}.html'.format(page))
        return render_template('plugin_rfplayer.html',
            clientid = client_id,
            client_detail = detail,
            mactive="clients",
            active = 'advanced',
            dongle_active = '',
            donglemenu_active = "general",
            manager = manager)

    except TemplateNotFound:
        abort(404)

@plugin_rfplayer_adm.route('/<client_id>/request/<mq_request>')
def rfplayer_request(client_id, mq_request):
    data = {}
    for k, v in request.args.iteritems():
        data[k] = v
    reply, msg = get_request(str(client_id), str(mq_request), data)
    if 'error'in msg and msg['error'] !="":
        return jsonify(result='error', reply=reply, content = msg)
    else :
        return jsonify(result='success', reply=reply, content = msg)

@plugin_rfplayer_adm.route('/<client_id>/<network_id>/controller')
def network_ctrl(client_id, network_id):
    detail = get_client_detail(client_id)
    abort = False
    if detail["status"] not in ["alive",  "starting"] : abort = True
    openzwaveInfo = get_openzwave_info(abort)
    if openzwaveInfo['error'] == 'Plugin timeout response.': abort = True
    managerState = get_manager_state(abort)
    if managerState['error'] == 'Plugin timeout response.': abort = True
    networkState = get_controller_state(network_id, abort)
    try:
        return render_template('plugin_ozwave_controller.html',
            clientid = client_id,
            client_detail = detail,
            mactive="clients",
            active = 'advanced',
            network_active = network_id,
            networkmenu_active = 'controller',
            openzwaveInfo = openzwaveInfo,
            managerState = managerState,
            network_state = networkState)

    except TemplateNotFound:
        abort(404)

@plugin_rfplayer_adm.route('/<client_id>/<network_id>/nodes')
def network_nodes(client_id, network_id):
    detail = get_client_detail(client_id)
    abort = False
    if detail["status"] not in ["alive",  "starting"] : abort = True
    openzwaveInfo = get_openzwave_info(abort)
    if openzwaveInfo['error'] == 'Plugin timeout response.': abort = True
    managerState = get_manager_state(abort)
    if managerState['error'] == 'Plugin timeout response.': abort = True
    networkState = get_controller_state(network_id, abort)
    if networkState['error'] == 'Plugin timeout response.': abort = True
    nodesState = get_controller_nodes(network_id,  abort)
    try:
        return render_template('plugin_ozwave_nodes.html',
            clientid = client_id,
            client_detail = detail,
            mactive="clients",
            active = 'advanced',
            network_active = network_id,
            networkmenu_active = 'nodes',
            openzwaveInfo = openzwaveInfo,
            managerState = managerState,
            network_state = networkState,
            nodes_state = nodesState['nodes'])

    except TemplateNotFound:
        abort(404)

@plugin_rfplayer_adm.route('/<client_id>/<network_id>/ctrltools')
def network_ctrl_tools(client_id, network_id):
    detail = get_client_detail(client_id)
    abort = False
    if detail["status"] not in ["alive",  "starting"] : abort = True
    openzwaveInfo = get_openzwave_info(abort)
    if openzwaveInfo['error'] == 'Plugin timeout response.': abort = True
    managerState = get_manager_state(abort)
    if managerState['error'] == 'Plugin timeout response.': abort = True
    networkState = get_controller_state(network_id, abort)
    try:
        return render_template('plugin_ozwave_ctrltools.html',
            clientid = client_id,
            client_detail = detail,
            mactive="clients",
            active = 'advanced',
            network_active = network_id,
            networkmenu_active = 'ctrltools',
            openzwaveInfo = openzwaveInfo,
            managerState = managerState,
            network_state = networkState)

    except TemplateNotFound:
        abort(404)

@plugin_rfplayer_adm.route('/<client_id>/<network_id>/network')
def network_netw(client_id, network_id):
    detail = get_client_detail(client_id)
    abort = False
    if detail["status"] not in ["alive",  "starting"] : abort = True
    openzwaveInfo = get_openzwave_info(abort)
    if openzwaveInfo['error'] == 'Plugin timeout response.': abort = True
    managerState = get_manager_state(abort)
    if managerState['error'] == 'Plugin timeout response.': abort = True
    networkState = get_controller_state(network_id, abort)
    try:
        return render_template('plugin_ozwave_network.html',
            clientid = client_id,
            client_detail = detail,
            mactive="clients",
            active = 'advanced',
            network_active = network_id,
            networkmenu_active = 'controller',
            openzwaveInfo = openzwaveInfo,
            managerState = managerState,
            network_state = networkState)

    except TemplateNotFound:
        abort(404)

@plugin_rfplayer_adm.route('/<client_id>/tools')
def plugin_tools(client_id):
    detail = get_client_detail(client_id)
    abort = False
    if detail["status"] not in ["alive",  "starting"] : abort = True
    openzwaveInfo = get_openzwave_info(abort)
    if openzwaveInfo['error'] == 'Plugin timeout response.': abort = True
    managerState = get_manager_state(abort)
    if managerState['error'] == 'Plugin timeout response.': abort = True
    allProducts = get_openzwave_all_products(abort)
    if allProducts['error'] == 'Plugin timeout response.': abort = True
    try:
        return render_template('plugin_ozwave_tools.html',
            clientid = client_id,
            client_detail = detail,
            mactive="clients",
            active = 'advanced',
            network_active = 'tools',
            networkmenu_active = '',
            openzwaveInfo = openzwaveInfo,
            managerState = managerState,
            ozw_products = allProducts)

    except TemplateNotFound:
        abort(404)

@plugin_rfplayer_adm.route('/<client_id>/<network_id>/<node_id>/infos')
def node_infos(client_id, network_id, node_id):
    nodeInfos = get_request(client_id, "ozwave.node.infos", {"networkId": network_id, "nodeId":node_id})
    if 'error'in nodeInfos and nodeInfos['error'] !="":
        return jsonify(result='error', data = nodeInfos)
    else :
        return jsonify(result='success', data = nodeInfos)
