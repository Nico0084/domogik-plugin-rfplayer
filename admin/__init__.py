# -*- coding: utf-8 -*-

### common imports
from flask import Blueprint, jsonify, request
from domogik.common.utils import get_packages_directory
from domogik.admin.application import render_template
from domogik.admin.views.clients import get_client_detail
from jinja2 import TemplateNotFound

### package specific imports
from domogik_packages.plugin_rfplayer.admin.views.manager_tools import get_manager_status, get_request

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

@plugin_rfplayer_adm.route('/<client_id>/tools')
def plugin_tools(client_id):
    detail = get_client_detail(client_id)
    abort = False
    manager = get_manager_status(abort)
    if manager['error'] == 'Plugin timeout response.': abort = True
    try:
        return render_template('tools.html',
            clientid = client_id,
            client_detail = detail,
            mactive="clients",
            active = 'advanced',
            dongle_active = 'tools',
            donglemenu_active = '',
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
