#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import argparse
import json
import os

from datetime import datetime
from oslo_utils import uuidutils

from karborclient.common.apiclient import exceptions
from karborclient.common import base
from karborclient.common import utils
from karborclient import utils as arg_utils


@utils.arg('--all-tenants',
           dest='all_tenants',
           metavar='<0|1>',
           nargs='?',
           type=int,
           const=1,
           default=0,
           help='Shows details for all tenants. Admin only.')
@utils.arg('--all_tenants',
           nargs='?',
           type=int,
           const=1,
           help=argparse.SUPPRESS)
@utils.arg('--name',
           metavar='<name>',
           default=None,
           help='Filters results by a name. Default=None.')
@utils.arg('--description',
           metavar='<description>',
           default=None,
           help='Filters results by a description. Default=None.')
@utils.arg('--status',
           metavar='<status>',
           default=None,
           help='Filters results by a status. Default=None.')
@utils.arg('--marker',
           metavar='<marker>',
           default=None,
           help='Begin returning plans that appear later in the plan '
                'list than that represented by this plan id. '
                'Default=None.')
@utils.arg('--limit',
           metavar='<limit>',
           default=None,
           help='Maximum number of plans to return. Default=None.')
@utils.arg('--sort_key',
           metavar='<sort_key>',
           default=None,
           help=argparse.SUPPRESS)
@utils.arg('--sort_dir',
           metavar='<sort_dir>',
           default=None,
           help=argparse.SUPPRESS)
@utils.arg('--sort',
           metavar='<key>[:<direction>]',
           default=None,
           help=(('Comma-separated list of sort keys and directions in the '
                  'form of <key>[:<asc|desc>]. '
                  'Valid keys: %s. '
                  'Default=None.') % ', '.join(base.SORT_KEY_VALUES)))
@utils.arg('--tenant',
           type=str,
           dest='tenant',
           nargs='?',
           metavar='<tenant>',
           help='Display information from single tenant (Admin only).')
def do_plan_list(cs, args):
    """Lists all plans."""

    all_tenants = 1 if args.tenant else \
        int(os.environ.get("ALL_TENANTS", args.all_tenants))
    search_opts = {
        'all_tenants': all_tenants,
        'project_id': args.tenant,
        'name': args.name,
        'description': args.description,
        'status': args.status,
    }

    if args.sort and (args.sort_key or args.sort_dir):
        raise exceptions.CommandError(
            'The --sort_key and --sort_dir arguments are deprecated and are '
            'not supported with --sort.')

    plans = cs.plans.list(search_opts=search_opts, marker=args.marker,
                          limit=args.limit, sort_key=args.sort_key,
                          sort_dir=args.sort_dir, sort=args.sort)

    key_list = ['Id', 'Name', 'Description', 'Provider id', 'Status']

    if args.sort_key or args.sort_dir or args.sort:
        sortby_index = None
    else:
        sortby_index = 0
    utils.print_list(plans, key_list, exclude_unavailable=True,
                     sortby_index=sortby_index)


@utils.arg('name',
           metavar='<name>',
           help='Plan name.')
@utils.arg('provider_id',
           metavar='<provider_id>',
           help='ID of provider.')
@utils.arg('resources',
           metavar='<id=type=name=extra_info,id=type=name=extra_info>',
           help='Resource in list must be a dict when creating'
                ' a plan. The keys of resource are id ,type, name and '
                'extra_info. The extra_info field is optional.')
@utils.arg('--parameters-json',
           type=str,
           dest='parameters_json',
           metavar='<parameters>',
           default=None,
           help='Plan parameters in json format.')
@utils.arg('--parameters',
           action='append',
           metavar='resource_type=<type>[,resource_id=<id>,key=val,...]',
           default=[],
           help='Plan parameters, may be specified multiple times. '
           'resource_type: type of resource to apply parameters. '
           'resource_id: limit the parameters to a specific resource. '
           'Other keys and values: according to provider\'s protect schema.'
           )
@utils.arg('--description',
           metavar='<description>',
           help='The description of a plan.')
def do_plan_create(cs, args):
    """Creates a plan."""
    if not uuidutils.is_uuid_like(args.provider_id):
        raise exceptions.CommandError(
            "Invalid provider id provided.")
    plan_resources = arg_utils.extract_resources(args)
    arg_utils.check_resources(cs, plan_resources)
    plan_parameters = arg_utils.extract_parameters(args)
    plan = cs.plans.create(args.name, args.provider_id, plan_resources,
                           plan_parameters, description=args.description)
    dict_format_list = {"resources", "parameters"}
    utils.print_dict(plan.to_dict(), dict_format_list=dict_format_list)


@utils.arg('plan',
           metavar='<plan>',
           help='ID of plan.')
def do_plan_show(cs, args):
    """Shows plan details."""
    plan = cs.plans.get(args.plan)
    dict_format_list = {"resources", "parameters"}
    utils.print_dict(plan.to_dict(), dict_format_list=dict_format_list)


@utils.arg('plan',
           metavar='<plan>',
           nargs="+",
           help='ID of plan.')
def do_plan_delete(cs, args):
    """Deletes plan."""
    failure_count = 0
    for plan_id in args.plan:
        try:
            plan = utils.find_resource(cs.plans, plan_id)
            cs.plans.delete(plan.id)
        except exceptions.NotFound:
            failure_count += 1
            print("Failed to delete '{0}'; plan not found".
                  format(plan_id))
    if failure_count == len(args.plan):
        raise exceptions.CommandError("Unable to find and delete any of the "
                                      "specified plan.")


@utils.arg("plan_id", metavar="<PLAN ID>",
           help="Id of plan to update.")
@utils.arg("--name", metavar="<name>",
           help="A name to which the plan will be renamed.")
@utils.arg("--resources", metavar="<id=type=name,id=type=name>",
           help="Resources to which the plan will be updated.")
@utils.arg("--status", metavar="<suspended|started>",
           help="status to which the plan will be updated.")
def do_plan_update(cs, args):
    """Updatas a plan."""
    data = {}
    if args.name is not None:
        data['name'] = args.name
    if args.resources is not None:
        plan_resources = arg_utils.extract_resources(args)
        data['resources'] = plan_resources
    if args.status is not None:
        data['status'] = args.status
    try:
        plan = utils.find_resource(cs.plans, args.plan_id)
        plan = cs.plans.update(plan.id, data)
    except exceptions.NotFound:
        raise exceptions.CommandError("Plan %s not found" % args.plan_id)
    else:
        utils.print_dict(plan.to_dict())


@utils.arg('provider_id',
           metavar='<provider_id>',
           help='Provider id.')
@utils.arg('checkpoint_id',
           metavar='<checkpoint_id>',
           help='Checkpoint id.')
@utils.arg('--restore_target',
           metavar='<restore_target>',
           help='Restore target.')
@utils.arg('--restore_username',
           metavar='<restore_username>',
           default=None,
           help='Username to restore target.')
@utils.arg('--restore_password',
           metavar='<restore_password>',
           default=None,
           help='Password to restore target.')
@utils.arg('--parameters-json',
           type=str,
           dest='parameters_json',
           metavar='<parameters>',
           default=None,
           help='Restore parameters in json format.')
@utils.arg('--parameters',
           action='append',
           metavar='resource_type=<type>[,resource_id=<id>,key=val,...]',
           default=[],
           help='Restore parameters, may be specified multiple times. '
           'resource_type: type of resource to apply parameters. '
           'resource_id: limit the parameters to a specific resource. '
           'Other keys and values: according to provider\'s restore schema.'
           )
def do_restore_create(cs, args):
    """Creates a restore."""
    if not uuidutils.is_uuid_like(args.provider_id):
        raise exceptions.CommandError(
            "Invalid provider id provided.")

    if not uuidutils.is_uuid_like(args.checkpoint_id):
        raise exceptions.CommandError(
            "Invalid checkpoint id provided.")

    restore_parameters = arg_utils.extract_parameters(args)
    restore_auth = None
    if args.restore_target is not None:
        if args.restore_username is None:
            raise exceptions.CommandError(
                "Must specify username for restore_target.")
        if args.restore_password is None:
            raise exceptions.CommandError(
                "Must specify password for restore_target.")
        restore_auth = {
            'type': 'password',
            'username': args.restore_username,
            'password': args.restore_password,
        }
    restore = cs.restores.create(args.provider_id, args.checkpoint_id,
                                 args.restore_target, restore_parameters,
                                 restore_auth)
    dict_format_list = {"parameters"}
    utils.print_dict(restore.to_dict(), dict_format_list=dict_format_list)


@utils.arg('--all-tenants',
           dest='all_tenants',
           metavar='<0|1>',
           nargs='?',
           type=int,
           const=1,
           default=0,
           help='Shows details for all tenants. Admin only.')
@utils.arg('--all_tenants',
           nargs='?',
           type=int,
           const=1,
           help=argparse.SUPPRESS)
@utils.arg('--status',
           metavar='<status>',
           default=None,
           help='Filters results by a status. Default=None.')
@utils.arg('--marker',
           metavar='<marker>',
           default=None,
           help='Begin returning restores that appear later in the restore '
                'list than that represented by this restore id. '
                'Default=None.')
@utils.arg('--limit',
           metavar='<limit>',
           default=None,
           help='Maximum number of restores to return. Default=None.')
@utils.arg('--sort_key',
           metavar='<sort_key>',
           default=None,
           help=argparse.SUPPRESS)
@utils.arg('--sort_dir',
           metavar='<sort_dir>',
           default=None,
           help=argparse.SUPPRESS)
@utils.arg('--sort',
           metavar='<key>[:<direction>]',
           default=None,
           help=(('Comma-separated list of sort keys and directions in the '
                  'form of <key>[:<asc|desc>]. '
                  'Valid keys: %s. '
                  'Default=None.') % ', '.join(base.SORT_KEY_VALUES)))
@utils.arg('--tenant',
           type=str,
           dest='tenant',
           nargs='?',
           metavar='<tenant>',
           help='Display information from single tenant (Admin only).')
def do_restore_list(cs, args):
    """Lists all restores."""

    all_tenants = 1 if args.tenant else \
        int(os.environ.get("ALL_TENANTS", args.all_tenants))
    search_opts = {
        'all_tenants': all_tenants,
        'project_id': args.tenant,
        'status': args.status,
    }

    if args.sort and (args.sort_key or args.sort_dir):
        raise exceptions.CommandError(
            'The --sort_key and --sort_dir arguments are deprecated and are '
            'not supported with --sort.')

    restores = cs.restores.list(search_opts=search_opts, marker=args.marker,
                                limit=args.limit, sort_key=args.sort_key,
                                sort_dir=args.sort_dir, sort=args.sort)

    key_list = ['Id', 'Project id', 'Provider id', 'Checkpoint id',
                'Restore target', 'Parameters', 'Status']

    if args.sort_key or args.sort_dir or args.sort:
        sortby_index = None
    else:
        sortby_index = 0
    formatters = {"Parameters": lambda obj: json.dumps(
        obj.parameters, indent=2, sort_keys=True)}
    utils.print_list(restores, key_list, exclude_unavailable=True,
                     sortby_index=sortby_index, formatters=formatters)


@utils.arg('restore',
           metavar='<restore>',
           help='ID of restore.')
def do_restore_show(cs, args):
    """Shows restore details."""
    restore = cs.restores.get(args.restore)
    dict_format_list = {"parameters"}
    utils.print_dict(restore.to_dict(), dict_format_list=dict_format_list)


def do_protectable_list(cs, args):
    """Lists all protectable types."""

    protectables = cs.protectables.list()

    key_list = ['Protectable type']

    utils.print_list(protectables, key_list, exclude_unavailable=True)


@utils.arg('protectable_type',
           metavar='<protectable_type>',
           help='Protectable type.')
def do_protectable_show(cs, args):
    """Shows protectable type details."""
    protectable = cs.protectables.get(args.protectable_type)
    utils.print_dict(protectable.to_dict())


@utils.arg('protectable_type',
           metavar='<protectable_type>',
           help='Protectable type.')
@utils.arg('protectable_id',
           metavar='<protectable_id>',
           help='Protectable instance id.')
@utils.arg('--parameters',
           type=str,
           nargs='*',
           metavar='<key=value>',
           default=None,
           help='Show a instance by parameters key and value pair. '
                'Default=None.')
def do_protectable_show_instance(cs, args):
    """Shows instance details."""
    search_opts = {
        'parameters': (arg_utils.extract_instances_parameters(args)
                       if args.parameters else None),
    }
    instance = cs.protectables.get_instance(args.protectable_type,
                                            args.protectable_id,
                                            search_opts=search_opts)
    dict_format_list = {"dependent_resources"}
    utils.print_dict(instance.to_dict(), dict_format_list=dict_format_list)


@utils.arg('protectable_type',
           metavar='<protectable_type>',
           help='Type of protectable.')
@utils.arg('--type',
           metavar='<type>',
           default=None,
           help='Filters results by a status. Default=None.')
@utils.arg('--marker',
           metavar='<marker>',
           default=None,
           help='Begin returning instances that appear later in the instance '
                'list than that represented by this instance id. '
                'Default=None.')
@utils.arg('--limit',
           metavar='<limit>',
           default=None,
           help='Maximum number of instances to return. Default=None.')
@utils.arg('--sort_key',
           metavar='<sort_key>',
           default=None,
           help=argparse.SUPPRESS)
@utils.arg('--sort_dir',
           metavar='<sort_dir>',
           default=None,
           help=argparse.SUPPRESS)
@utils.arg('--sort',
           metavar='<key>[:<direction>]',
           default=None,
           help=(('Comma-separated list of sort keys and directions in the '
                  'form of <key>[:<asc|desc>]. '
                  'Valid keys: %s. '
                  'Default=None.') % ', '.join(base.SORT_KEY_VALUES)))
@utils.arg('--parameters',
           type=str,
           nargs='*',
           metavar='<key=value>',
           default=None,
           help='List instances by parameters key and value pair. '
                'Default=None.')
def do_protectable_list_instances(cs, args):
    """Lists all protectable instances."""

    search_opts = {
        'type': args.type,
        'parameters': (arg_utils.extract_instances_parameters(args)
                       if args.parameters else None),
    }

    if args.sort and (args.sort_key or args.sort_dir):
        raise exceptions.CommandError(
            'The --sort_key and --sort_dir arguments are deprecated and are '
            'not supported with --sort.')

    instances = cs.protectables.list_instances(
        args.protectable_type, search_opts=search_opts,
        marker=args.marker, limit=args.limit,
        sort_key=args.sort_key,
        sort_dir=args.sort_dir, sort=args.sort)

    key_list = ['Id', 'Type', 'Name', 'Dependent resources', 'Extra info']

    if args.sort_key or args.sort_dir or args.sort:
        sortby_index = None
    else:
        sortby_index = 0

    formatters = {"Dependent resources": lambda obj: json.dumps(
        obj.dependent_resources, indent=2, sort_keys=True)}
    utils.print_list(instances, key_list, exclude_unavailable=True,
                     sortby_index=sortby_index, formatters=formatters)


@utils.arg('provider_id',
           metavar='<provider_id>',
           help='Id of provider.')
def do_provider_show(cs, args):
    """Shows provider details."""
    provider = cs.providers.get(args.provider_id)
    dict_format_list = {"extended_info_schema"}
    utils.print_dict(provider.to_dict(), dict_format_list=dict_format_list)


@utils.arg('--name',
           metavar='<name>',
           default=None,
           help='Filters results by a name. Default=None.')
@utils.arg('--description',
           metavar='<description>',
           default=None,
           help='Filters results by a description. Default=None.')
@utils.arg('--marker',
           metavar='<marker>',
           default=None,
           help='Begin returning providers that appear later in the provider '
                'list than that represented by this provider id. '
                'Default=None.')
@utils.arg('--limit',
           metavar='<limit>',
           default=None,
           help='Maximum number of providers to return. Default=None.')
@utils.arg('--sort_key',
           metavar='<sort_key>',
           default=None,
           help=argparse.SUPPRESS)
@utils.arg('--sort_dir',
           metavar='<sort_dir>',
           default=None,
           help=argparse.SUPPRESS)
@utils.arg('--sort',
           metavar='<key>[:<direction>]',
           default=None,
           help=(('Comma-separated list of sort keys and directions in the '
                  'form of <key>[:<asc|desc>]. '
                  'Valid keys: %s. '
                  'Default=None.') % ', '.join(base.SORT_KEY_VALUES)))
def do_provider_list(cs, args):
    """Lists all providers."""

    search_opts = {
        'name': args.name,
        'description': args.description,
    }

    if args.sort and (args.sort_key or args.sort_dir):
        raise exceptions.CommandError(
            'The --sort_key and --sort_dir arguments are deprecated and are '
            'not supported with --sort.')

    providers = cs.providers.list(search_opts=search_opts, marker=args.marker,
                                  limit=args.limit, sort_key=args.sort_key,
                                  sort_dir=args.sort_dir, sort=args.sort)

    key_list = ['Id', 'Name', 'Description']

    if args.sort_key or args.sort_dir or args.sort:
        sortby_index = None
    else:
        sortby_index = 0
    utils.print_list(providers, key_list, exclude_unavailable=True,
                     sortby_index=sortby_index)


@utils.arg('provider_id',
           metavar='<provider_id>',
           help='ID of provider.')
@utils.arg('plan_id',
           metavar='<plan_id>',
           help='ID of plan.')
@utils.arg('--extra_info',
           type=str,
           nargs='*',
           metavar='<key=value>',
           default=None,
           help='The extra info of a checkpoint.')
def do_checkpoint_create(cs, args):
    """Creates a checkpoint."""

    checkpoint_extra_info = None
    if args.extra_info is not None:
        checkpoint_extra_info = arg_utils.extract_extra_info(args)
    checkpoint = cs.checkpoints.create(args.provider_id, args.plan_id,
                                       checkpoint_extra_info)
    dict_format_list = {"protection_plan"}
    json_format_list = {"resource_graph"}
    utils.print_dict(checkpoint.to_dict(), dict_format_list=dict_format_list,
                     json_format_list=json_format_list)


@utils.arg('provider_id',
           metavar='<provider_id>',
           help='ID of provider.')
@utils.arg('--plan_id',
           metavar='<plan_id>',
           default=None,
           help='Filters results by a plan ID. Default=None.')
@utils.arg('--start_date',
           type=str,
           metavar='<start_date>',
           default=None,
           help='Filters results by a start date("Y-m-d"). Default=None.')
@utils.arg('--end_date',
           type=str,
           metavar='<end_date>',
           default=None,
           help='Filters results by a end date("Y-m-d"). Default=None.')
@utils.arg('--project_id',
           metavar='<project_id>',
           default=None,
           help='Filters results by a project ID. Default=None.')
@utils.arg('--marker',
           metavar='<marker>',
           default=None,
           help='Begin returning checkpoints that appear later in the '
                'checkpoint list than that represented by this checkpoint id. '
                'Default=None.')
@utils.arg('--limit',
           metavar='<limit>',
           default=None,
           help='Maximum number of checkpoints to return. Default=None.')
@utils.arg('--sort_key',
           metavar='<sort_key>',
           default=None,
           help=argparse.SUPPRESS)
@utils.arg('--sort_dir',
           metavar='<sort_dir>',
           default=None,
           help=argparse.SUPPRESS)
@utils.arg('--sort',
           metavar='<key>[:<direction>]',
           default=None,
           help=(('Comma-separated list of sort keys and directions in the '
                  'form of <key>[:<asc|desc>]. '
                  'Valid keys: %s. '
                  'Default=None.') % ', '.join(base.SORT_KEY_VALUES)))
def do_checkpoint_list(cs, args):
    """Lists all checkpoints."""
    if args.plan_id is not None:
        if not uuidutils.is_uuid_like(args.plan_id):
            raise exceptions.CommandError('The plan_id must be a uuid')

    if args.start_date:
        try:
            datetime.strptime(
                args.start_date, "%Y-%m-%d")
        except (ValueError, SyntaxError):
            raise exceptions.CommandError(
                "The format of start_date should be %Y-%m-%d")

    if args.end_date:
        try:
            datetime.strptime(
                args.end_date, "%Y-%m-%d")
        except (ValueError, SyntaxError):
            raise exceptions.CommandError(
                "The format of end_date should be %Y-%m-%d")

    search_opts = {
        'plan_id': args.plan_id,
        'start_date': args.start_date,
        'end_date': args.end_date,
        'project_id': args.project_id,
    }

    if args.sort and (args.sort_key or args.sort_dir):
        raise exceptions.CommandError(
            'The --sort_key and --sort_dir arguments are deprecated and are '
            'not supported with --sort.')

    checkpoints = cs.checkpoints.list(
        provider_id=args.provider_id, search_opts=search_opts,
        marker=args.marker, limit=args.limit, sort_key=args.sort_key,
        sort_dir=args.sort_dir, sort=args.sort)

    key_list = ['Id', 'Project id', 'Status', 'Protection plan', 'Metadata',
                'Created at']

    if args.sort_key or args.sort_dir or args.sort:
        sortby_index = None
    else:
        sortby_index = 0
    formatters = {"Protection plan": lambda obj: json.dumps(
        obj.protection_plan, indent=2, sort_keys=True)}
    utils.print_list(checkpoints, key_list, exclude_unavailable=True,
                     sortby_index=sortby_index, formatters=formatters)


@utils.arg('provider_id',
           metavar='<provider_id>',
           help='Id of provider.')
@utils.arg('checkpoint_id',
           metavar='<checkpoint_id>',
           help='Id of checkpoint.')
def do_checkpoint_show(cs, args):
    """Shows checkpoint details."""
    checkpoint = cs.checkpoints.get(args.provider_id, args.checkpoint_id)
    dict_format_list = {"protection_plan"}
    json_format_list = {"resource_graph"}
    utils.print_dict(checkpoint.to_dict(), dict_format_list=dict_format_list,
                     json_format_list=json_format_list)


@utils.arg('provider_id',
           metavar='<provider_id>',
           help='Id of provider.')
@utils.arg('checkpoint',
           metavar='<checkpoint>',
           nargs="+",
           help='ID of checkpoint.')
def do_checkpoint_delete(cs, args):
    """Deletes checkpoints."""
    failure_count = 0
    for checkpoint_id in args.checkpoint:
        try:
            checkpoint = cs.checkpoints.get(args.provider_id,
                                            checkpoint_id)
            cs.checkpoints.delete(args.provider_id, checkpoint.id)
        except exceptions.NotFound:
            failure_count += 1
            print("Failed to delete '{0}'; checkpoint not found".
                  format(checkpoint_id))
    if failure_count == len(args.checkpoint):
        raise exceptions.CommandError("Unable to find and delete any of the "
                                      "specified checkpoint.")


@utils.arg('--all-tenants',
           dest='all_tenants',
           metavar='<0|1>',
           nargs='?',
           type=int,
           const=1,
           default=0,
           help='Shows details for all tenants. Admin only.')
@utils.arg('--all_tenants',
           nargs='?',
           type=int,
           const=1,
           help=argparse.SUPPRESS)
@utils.arg('--name',
           metavar='<name>',
           default=None,
           help='Filters results by a name. Default=None.')
@utils.arg('--type',
           metavar='<type>',
           default=None,
           help='Filters results by a type. Default=None.')
@utils.arg('--properties',
           metavar='<properties>',
           default=None,
           help='Filters results by a properties. Default=None.')
@utils.arg('--marker',
           metavar='<marker>',
           default=None,
           help='Begin returning triggers that appear later in the trigger '
                'list than that represented by this trigger id. '
                'Default=None.')
@utils.arg('--limit',
           metavar='<limit>',
           default=None,
           help='Maximum number of triggers to return. Default=None.')
@utils.arg('--sort_key',
           metavar='<sort_key>',
           default=None,
           help=argparse.SUPPRESS)
@utils.arg('--sort_dir',
           metavar='<sort_dir>',
           default=None,
           help=argparse.SUPPRESS)
@utils.arg('--sort',
           metavar='<key>[:<direction>]',
           default=None,
           help=(('Comma-separated list of sort keys and directions in the '
                  'form of <key>[:<asc|desc>]. '
                  'Valid keys: %s. '
                  'Default=None.') % ', '.join(base.SORT_KEY_VALUES)))
@utils.arg('--tenant',
           type=str,
           dest='tenant',
           nargs='?',
           metavar='<tenant>',
           help='Display information from single tenant (Admin only).')
def do_trigger_list(cs, args):
    """Lists all triggers."""

    all_tenants = 1 if args.tenant else \
        int(os.environ.get("ALL_TENANTS", args.all_tenants))
    search_opts = {
        'all_tenants': all_tenants,
        'project_id': args.tenant,
        'name': args.name,
        'type': args.type,
        'properties': args.properties,
    }

    if args.sort and (args.sort_key or args.sort_dir):
        raise exceptions.CommandError(
            'The --sort_key and --sort_dir arguments are deprecated and are '
            'not supported with --sort.')

    triggers = cs.triggers.list(search_opts=search_opts, marker=args.marker,
                                limit=args.limit, sort_key=args.sort_key,
                                sort_dir=args.sort_dir, sort=args.sort)

    key_list = ['Id', 'Name', 'Type', 'Properties']

    if args.sort_key or args.sort_dir or args.sort:
        sortby_index = None
    else:
        sortby_index = 0

    formatters = {"Properties": lambda obj: json.dumps(
        obj.properties, indent=2, sort_keys=True)}
    utils.print_list(triggers, key_list, exclude_unavailable=True,
                     sortby_index=sortby_index, formatters=formatters)


@utils.arg('name',
           metavar='<name>',
           help='Trigger name.')
@utils.arg('type',
           metavar='<type>',
           help='Type of trigger.')
@utils.arg('properties',
           metavar='<key=value,key=value>',
           help='Properties of trigger.')
def do_trigger_create(cs, args):
    """Creates a trigger."""
    trigger_properties = arg_utils.extract_properties(args)
    trigger = cs.triggers.create(args.name, args.type, trigger_properties)
    dict_format_list = {"properties"}
    utils.print_dict(trigger.to_dict(), dict_format_list=dict_format_list)


@utils.arg("trigger_id", metavar="<TRIGGER ID>",
           help="Id of trigger to update.")
@utils.arg("--name", metavar="<name>",
           help="A new name to which the trigger will be renamed.")
@utils.arg("--properties", metavar="<key=value,key=value>",
           help="Properties of trigger which will be updated.")
def do_trigger_update(cs, args):
    """Update a trigger."""
    trigger_info = {}
    trigger_properties = arg_utils.extract_properties(args)
    trigger_info['name'] = args.name
    trigger_info['properties'] = trigger_properties
    trigger = cs.triggers.update(args.trigger_id, trigger_info)
    dict_format_list = {"properties"}
    utils.print_dict(trigger.to_dict(), dict_format_list=dict_format_list)


@utils.arg('trigger',
           metavar='<trigger>',
           help='ID of trigger.')
def do_trigger_show(cs, args):
    """Shows trigger details."""
    trigger = cs.triggers.get(args.trigger)
    dict_format_list = {"properties"}
    utils.print_dict(trigger.to_dict(), dict_format_list=dict_format_list)


@utils.arg('trigger',
           metavar='<trigger>',
           nargs="+",
           help='ID of trigger.')
def do_trigger_delete(cs, args):
    """Deletes trigger."""
    failure_count = 0
    for trigger_id in args.trigger:
        try:
            trigger = utils.find_resource(cs.triggers, trigger_id)
            cs.triggers.delete(trigger.id)
        except exceptions.NotFound:
            failure_count += 1
            print("Failed to delete '{0}'; trigger not found".
                  format(trigger_id))
    if failure_count == len(args.trigger):
        raise exceptions.CommandError("Unable to find and delete any of the "
                                      "specified trigger.")


@utils.arg('--all-tenants',
           dest='all_tenants',
           metavar='<0|1>',
           nargs='?',
           type=int,
           const=1,
           default=0,
           help='Shows details for all tenants. Admin only.')
@utils.arg('--all_tenants',
           nargs='?',
           type=int,
           const=1,
           help=argparse.SUPPRESS)
@utils.arg('--name',
           metavar='<name>',
           default=None,
           help='Filters results by a name. Default=None.')
@utils.arg('--operation_type',
           metavar='<operation_type>',
           default=None,
           help='Filters results by a type. Default=None.')
@utils.arg('--trigger_id',
           metavar='<trigger_id>',
           default=None,
           help='Filters results by a trigger id. Default=None.')
@utils.arg('--operation_definition',
           metavar='<operation_definition>',
           default=None,
           help='Filters results by a operation definition. Default=None.')
@utils.arg('--marker',
           metavar='<marker>',
           default=None,
           help='Begin returning resources that appear later in the '
                'list than that represented by this id. '
                'Default=None.')
@utils.arg('--limit',
           metavar='<limit>',
           default=None,
           help='Maximum number to return. Default=None.')
@utils.arg('--sort_key',
           metavar='<sort_key>',
           default=None,
           help=argparse.SUPPRESS)
@utils.arg('--sort_dir',
           metavar='<sort_dir>',
           default=None,
           help=argparse.SUPPRESS)
@utils.arg('--sort',
           metavar='<key>[:<direction>]',
           default=None,
           help=(('Comma-separated list of sort keys and directions in the '
                  'form of <key>[:<asc|desc>]. '
                  'Valid keys: %s. '
                  'Default=None.') % ', '.join(base.SORT_KEY_VALUES)))
@utils.arg('--tenant',
           type=str,
           dest='tenant',
           nargs='?',
           metavar='<tenant>',
           help='Display information from single tenant (Admin only).')
def do_scheduledoperation_list(cs, args):
    """Lists all scheduledoperations."""

    all_tenants = 1 if args.tenant else \
        int(os.environ.get("ALL_TENANTS", args.all_tenants))
    search_opts = {
        'all_tenants': all_tenants,
        'project_id': args.tenant,
        'name': args.name,
        'operation_type': args.operation_type,
        'trigger_id': args.trigger_id,
        'operation_definition': args.operation_definition,
    }

    if args.sort and (args.sort_key or args.sort_dir):
        raise exceptions.CommandError(
            'The --sort_key and --sort_dir arguments are deprecated and are '
            'not supported with --sort.')

    scheduledoperations = cs.scheduled_operations.list(
        search_opts=search_opts, marker=args.marker, limit=args.limit,
        sort_key=args.sort_key, sort_dir=args.sort_dir, sort=args.sort)

    key_list = ['Id', 'Name', 'OperationType', 'TriggerId',
                'OperationDefinition']

    if args.sort_key or args.sort_dir or args.sort:
        sortby_index = None
    else:
        sortby_index = 0
    utils.print_list(scheduledoperations, key_list, exclude_unavailable=True,
                     sortby_index=sortby_index)


@utils.arg('name',
           metavar='<name>',
           help='Trigger name.')
@utils.arg('operation_type',
           metavar='<operation_type>',
           help='Operation Type of scheduled operation.')
@utils.arg('trigger_id',
           metavar='<trigger_id>',
           help='Trigger id of scheduled operation.')
@utils.arg('operation_definition',
           metavar='<key=value,key=value>',
           help='Operation definition of scheduled operation.')
def do_scheduledoperation_create(cs, args):
    """Creates a scheduled operation."""
    operation_definition = arg_utils.extract_operation_definition(args)
    scheduledoperation = cs.scheduled_operations.create(args.name,
                                                        args.operation_type,
                                                        args.trigger_id,
                                                        operation_definition)
    dict_format_list = {"operation_definition"}
    utils.print_dict(scheduledoperation.to_dict(),
                     dict_format_list=dict_format_list)


@utils.arg('scheduledoperation',
           metavar='<scheduledoperation>',
           help='ID of scheduled operation.')
def do_scheduledoperation_show(cs, args):
    """Shows scheduledoperation details."""
    scheduledoperation = cs.scheduled_operations.get(args.scheduledoperation)
    dict_format_list = {"operation_definition"}
    utils.print_dict(scheduledoperation.to_dict(),
                     dict_format_list=dict_format_list)


@utils.arg('scheduledoperation',
           metavar='<scheduledoperation>',
           nargs="+",
           help='ID of scheduled operation.')
def do_scheduledoperation_delete(cs, args):
    """Deletes a scheduled operation."""
    failure_count = 0
    for scheduledoperation_id in args.scheduledoperation:
        try:
            scheduledoperation = utils.find_resource(cs.scheduled_operations,
                                                     scheduledoperation_id)
            cs.scheduled_operations.delete(scheduledoperation.id)
        except exceptions.NotFound:
            failure_count += 1
            print("Failed to delete '{0}'; scheduledoperation not found".
                  format(scheduledoperation_id))
    if failure_count == len(args.scheduledoperation):
        raise exceptions.CommandError("Unable to find and delete any of the "
                                      "specified scheduled operation.")
