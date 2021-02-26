import re
from datetime import datetime

import pytz
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.db import transaction
from django.contrib.gis.geos import Point, GEOSGeometry
from ledger.accounts.models import EmailUser, Document
from rest_framework import serializers

from disturbance.components.main.decorators import timeit
from disturbance.components.proposals.models import ProposalDocument, ProposalUserAction, ApiarySite, SiteCategory, \
    ProposalApiaryTemporaryUse, TemporaryUseApiarySite, ApiarySiteOnProposal, Proposal
from disturbance.components.proposals.serializers import SaveProposalSerializer

from disturbance.components.approvals.models import Approval
from disturbance.components.proposals.models import (
    SiteTransferApiarySite,
    ApiaryChecklistQuestion,
    ApiaryChecklistAnswer,
    QuestionOption,
    MasterlistQuestion,
    ProposalTypeSection,
    SectionQuestion,
)
from disturbance.components.proposals.serializers_apiary import (
    ProposalApiarySerializer,
    ProposalApiaryTemporaryUseSerializer,
    ApiarySiteSerializer, TemporaryUseApiarySiteSerializer,
    ApiarySiteOnProposalDraftGeometrySaveSerializer
)
from disturbance.components.proposals.email import send_submit_email_notification, send_external_submit_email_notification
from disturbance.components.organisations.models import Organisation

import traceback
import os
import json

import logging

from disturbance.settings import RESTRICTED_RADIUS, TIME_ZONE
from disturbance.utils import convert_moment_str_to_python_datetime_obj

logger = logging.getLogger(__name__)

def create_data_from_form(schema, post_data, file_data, post_data_index=None,special_fields=[],assessor_data=False):
    data = {}
    special_fields_list = []
    assessor_data_list = []
    comment_data_list = {}
    special_fields_search = SpecialFieldsSearch(special_fields)
    if assessor_data:
        assessor_fields_search = AssessorDataSearch()
        comment_fields_search = CommentDataSearch()
    try:
        for item in schema:
            data.update(_create_data_from_item(item, post_data, file_data, 0, ''))
            #_create_data_from_item(item, post_data, file_data, 0, '')
            special_fields_search.extract_special_fields(item, post_data, file_data, 0, '')
            if assessor_data:
                assessor_fields_search.extract_special_fields(item, post_data, file_data, 0, '')
                comment_fields_search.extract_special_fields(item, post_data, file_data, 0, '')
        special_fields_list = special_fields_search.special_fields
        if assessor_data:
            assessor_data_list = assessor_fields_search.assessor_data
            comment_data_list = comment_fields_search.comment_data
    except:
        traceback.print_exc()
    if assessor_data:
        return [data],special_fields_list,assessor_data_list,comment_data_list

    return [data],special_fields_list


def _extend_item_name(name, suffix, repetition):
    return '{}{}-{}'.format(name, suffix, repetition)

def _create_data_from_item(item, post_data, file_data, repetition, suffix):
    item_data = {}

    if 'name' in item:
        extended_item_name = item['name']
    else:
        raise Exception('Missing name in item %s' % item['label'])

    #import ipdb; ipdb.set_trace()
    if 'children' not in item:
        if item['type'] in ['checkbox' 'declaration']:
            #item_data[item['name']] = post_data[item['name']]
            #import ipdb; ipdb.set_trace()
            item_data[item['name']] = extended_item_name in post_data
        elif item['type'] == 'file':
            if extended_item_name in file_data:
                item_data[item['name']] = str(file_data.get(extended_item_name))
                # TODO save the file here
            elif extended_item_name + '-existing' in post_data and len(post_data[extended_item_name + '-existing']) > 0:
                item_data[item['name']] = post_data.get(extended_item_name + '-existing')
            else:
                item_data[item['name']] = ''
        else:
            if extended_item_name in post_data:
                if item['type'] == 'multi-select':
                    item_data[item['name']] = post_data.getlist(extended_item_name)
                else:
                    item_data[item['name']] = post_data.get(extended_item_name)
    else:
        if 'repetition' in item:
            item_data = generate_item_data(extended_item_name,item,item_data,post_data,file_data,len(post_data[item['name']]),suffix)
        else:
            #import ipdb; ipdb.set_trace()
            item_data = generate_item_data(extended_item_name, item, item_data, post_data, file_data,1,suffix)


    if 'conditions' in item:
        for condition in list(item['conditions'].keys()):
            for child in item['conditions'][condition]:
                item_data.update(_create_data_from_item(child, post_data, file_data, repetition, suffix))

    #import ipdb; ipdb.set_trace()
    return item_data

def generate_item_data(item_name,item,item_data,post_data,file_data,repetition,suffix):
    item_data_list = []
    for rep in range(0, repetition):
        #import ipdb; ipdb.set_trace()
        child_data = {}
        for child_item in item.get('children'):
            child_data.update(_create_data_from_item(child_item, post_data, file_data, 0,
                                                     '{}-{}'.format(suffix, rep)))
        item_data_list.append(child_data)

        item_data[item['name']] = item_data_list
    return item_data

class AssessorDataSearch(object):

    def __init__(self,lookup_field='canBeEditedByAssessor'):
        self.lookup_field = lookup_field
        self.assessor_data = []

    def extract_assessor_data(self,item,post_data):
        values = []
        res = {
            'name': item,
            'assessor': '',
            'referrals':[]
        }
        for k in post_data:
            if re.match(item,k):
                values.append({k:post_data[k]})
        if values:
            for v in values:
                for k,v in v.items():
                    parts = k.split('{}-'.format(item))
                    if len(parts) > 1:
                        # split parts to see if referall
                        ref_parts = parts[1].split('Referral-')
                        if len(ref_parts) > 1:
                            # Referrals
                            res['referrals'].append({
                                'value':v,
                                'email':ref_parts[1],
                                'full_name': EmailUser.objects.get(email=ref_parts[1].lower()).get_full_name()
                            })
                        elif k.split('-')[-1].lower() == 'assessor':
                            # Assessor
                            res['assessor'] = v

        return res

    def extract_special_fields(self,item, post_data, file_data, repetition, suffix):
        item_data = {}
        if 'name' in item:
            extended_item_name = item['name']
        else:
            raise Exception('Missing name in item %s' % item['label'])

        if 'children' not in item:
            if 'conditions' in item:
                for condition in list(item['conditions'].keys()):
                    for child in item['conditions'][condition]:
                        item_data.update(self.extract_special_fields(child, post_data, file_data, repetition, suffix))

            if item.get(self.lookup_field):
                self.assessor_data.append(self.extract_assessor_data(extended_item_name,post_data))

        else:
            if 'repetition' in item:
                item_data = self.generate_item_data_special_field(extended_item_name,item,item_data,post_data,file_data,len(post_data[item['name']]),suffix)
            else:
                item_data = self.generate_item_data_special_field(extended_item_name, item, item_data, post_data, file_data,1,suffix)

            if 'conditions' in item:
                for condition in list(item['conditions'].keys()):
                    for child in item['conditions'][condition]:
                        item_data.update(self.extract_special_fields(child, post_data, file_data, repetition, suffix))

        return item_data

    def generate_item_data_special_field(self,item_name,item,item_data,post_data,file_data,repetition,suffix):
        item_data_list = []
        for rep in range(0, repetition):
            child_data = {}
            for child_item in item.get('children'):
                child_data.update(self.extract_special_fields(child_item, post_data, file_data, 0,
                                                         '{}-{}'.format(suffix, rep)))
            item_data_list.append(child_data)

            item_data[item['name']] = item_data_list
        return item_data

class CommentDataSearch(object):

    def __init__(self,lookup_field='canBeEditedByAssessor'):
        self.lookup_field = lookup_field
        self.comment_data = {}

    def extract_comment_data_original(self,item,post_data):
        res = {}
        values = []
        for k in post_data:
            if re.match(item,k):
                values.append({k:post_data[k]})
        if values:
            #import ipdb; ipdb.set_trace()
            for v in values:
                for k,v in v.items():
                    parts = k.split('{}'.format(item))
                    if len(parts) > 1:
                        ref_parts = parts[1].split('-comment-field')
                        if len(ref_parts) > 1:
                            if len(ref_parts)==2 and ref_parts[0]=='' and ref_parts[1]=='':
                                print(v)
                                #if('{}'.format(item)=="Section0-1"):
                                #print(item,v, parts, ref_parts)
                            res = {'{}'.format(item):v}
        return res

    def extract_comment_data(self,item,post_data):
        res = {}
        values = []
        for k in post_data:
            if re.match(item,k):
                values.append({k:post_data[k]})
        if values:
            #import ipdb; ipdb.set_trace()
            for v in values:
                for k,v in v.items():
                    parts = k.split('{}'.format(item))
                    if len(parts) > 1:
                        ref_parts = parts[1].split('-comment-field')
                        if len(ref_parts) > 1:
                            if len(ref_parts)==2 and ref_parts[0]=='' and ref_parts[1]=='':
                                res = {'{}'.format(item):v}
        return res

    def extract_special_fields(self,item, post_data, file_data, repetition, suffix):
        item_data = {}
        if 'name' in item:
            extended_item_name = item['name']
        else:
            raise Exception('Missing name in item %s' % item['label'])

        if 'children' not in item:
            #print(item, extended_item_name)
            self.comment_data.update(self.extract_comment_data(extended_item_name,post_data))

        else:
            if 'repetition' in item:
                item_data = self.generate_item_data_special_field(extended_item_name,item,item_data,post_data,file_data,len(post_data[item['name']]),suffix)
            else:
                item_data = self.generate_item_data_special_field(extended_item_name, item, item_data, post_data, file_data,1,suffix)


        if 'conditions' in item:
            for condition in list(item['conditions'].keys()):
                for child in item['conditions'][condition]:
                    item_data.update(self.extract_special_fields(child, post_data, file_data, repetition, suffix))

        return item_data

    def generate_item_data_special_field(self,item_name,item,item_data,post_data,file_data,repetition,suffix):
        item_data_list = []
        for rep in range(0, repetition):
            child_data = {}
            for child_item in item.get('children'):
                child_data.update(self.extract_special_fields(child_item, post_data, file_data, 0,
                                                         '{}-{}'.format(suffix, rep)))
            item_data_list.append(child_data)

            item_data[item['name']] = item_data_list
        return item_data

class SpecialFieldsSearch(object):

    def __init__(self,lookable_fields):
        self.lookable_fields = lookable_fields
        self.special_fields = {}

    def extract_special_fields(self,item, post_data, file_data, repetition, suffix):
        item_data = {}
        if 'name' in item:
            extended_item_name = item['name']
        else:
            raise Exception('Missing name in item %s' % item['label'])

        if 'children' not in item:
            for f in self.lookable_fields:
                if item['type'] in ['checkbox' 'declaration']:
                    val = None
                    val = item.get(f,None)
                    if val:
                        item_data[f] = extended_item_name in post_data
                        self.special_fields.update(item_data)
                else:
                    if extended_item_name in post_data:
                        val = None
                        val = item.get(f,None)
                        if val:
                            if item['type'] == 'multi-select':
                                item_data[f] = ','.join(post_data.getlist(extended_item_name))
                            else:
                                item_data[f] = post_data.get(extended_item_name)
                            self.special_fields.update(item_data)
        else:
            if 'repetition' in item:
                item_data = self.generate_item_data_special_field(extended_item_name,item,item_data,post_data,file_data,len(post_data[item['name']]),suffix)
            else:
                item_data = self.generate_item_data_special_field(extended_item_name, item, item_data, post_data, file_data,1,suffix)


        if 'conditions' in item:
            for condition in list(item['conditions'].keys()):
                for child in item['conditions'][condition]:
                    item_data.update(self.extract_special_fields(child, post_data, file_data, repetition, suffix))

        return item_data

    def generate_item_data_special_field(self,item_name,item,item_data,post_data,file_data,repetition,suffix):
        item_data_list = []
        for rep in range(0, repetition):
            child_data = {}
            for child_item in item.get('children'):
                child_data.update(self.extract_special_fields(child_item, post_data, file_data, 0,
                                                         '{}-{}'.format(suffix, rep)))
            item_data_list.append(child_data)

            item_data[item['name']] = item_data_list
        return item_data


# -------------------------------------------------------------------------------------------------------------
# APIARY Section starts here
# -------------------------------------------------------------------------------------------------------------

def save_proponent_data(instance, request, viewset):
    if instance.application_type.name == 'Site Transfer':
    #if instance.application_type.name == ApplicationType.SITE_TRANSFER:
        save_proponent_data_apiary_site_transfer(instance, request, viewset)
        instance.log_user_action(ProposalUserAction.APIARY_ACTION_SAVE_APPLICATION.format(instance.lodgement_number), request)
    elif instance.apiary_group_application_type:
        save_proponent_data_apiary(instance, request, viewset)
        instance.log_user_action(ProposalUserAction.APIARY_ACTION_SAVE_APPLICATION.format(instance.lodgement_number), request)
    else:
        save_proponent_data_disturbance(instance,request,viewset)

def save_proponent_data_apiary_site_transfer(proposal_obj, request, viewset):
    with transaction.atomic():
        try:
            data = {
            }

            try:
                schema = request.data.get('schema')
            except:
                schema = request.POST.get('schema')

            sc = json.loads(schema) if schema else {}

            proposal_apiary_data = sc.get('proposal_apiary', None)
            if proposal_apiary_data:
                #import ipdb;ipdb.set_trace()
                save_checklist_answers('applicant', proposal_apiary_data.get('applicant_checklist_answers'))

            #import ipdb; ipdb.set_trace()
            transferee_email_text = request.data.get('transferee_email_text')
            if transferee_email_text:
                proposal_obj.proposal_apiary.transferee_email_text = transferee_email_text
                proposal_obj.proposal_apiary.save()
            selected_licence_holder_str = request.data.get('selected_licence_holder')
            selected_licence_holder = json.loads(selected_licence_holder_str) if selected_licence_holder_str else ''
            if selected_licence_holder:
                # for each path, ensure we remove any previously user selected licence holder data (target_approval, transferee, target_approval_organisation)
                if not selected_licence_holder.get('id'):
                    # new licence creation required
                    if selected_licence_holder.get('organisation_id'):
                        proposal_obj.proposal_apiary.target_approval_organisation = Organisation.objects.get(id=selected_licence_holder.get('organisation_id'))
                        proposal_obj.proposal_apiary.transferee = EmailUser.objects.get(id=selected_licence_holder.get('transferee_id'))
                        proposal_obj.proposal_apiary.target_approval = None
                    else:
                        proposal_obj.proposal_apiary.transferee = EmailUser.objects.get(id=selected_licence_holder.get('transferee_id'))
                        proposal_obj.proposal_apiary.target_approval_organisation = None
                        proposal_obj.proposal_apiary.target_approval = None
                else:
                    # Apiary licence already exists
                    proposal_obj.proposal_apiary.transferee = None
                    proposal_obj.proposal_apiary.target_approval_organisation = None
                    proposal_obj.proposal_apiary.target_approval = Approval.objects.get(id=selected_licence_holder.get('id'))
                # save for all paths
                proposal_obj.proposal_apiary.save()


            apiary_sites_local = request.data.get('apiary_sites_local')
            if apiary_sites_local:
                for site in json.loads(apiary_sites_local):
                    #print(site.get('id'))
                    #print(site.get('checked'))
                    checked_value = bool(site.get('checked'))
                    site_transfer_apiary_site = SiteTransferApiarySite.objects.get(
                            proposal_apiary=proposal_obj.proposal_apiary, 
                            apiary_site_on_approval__apiary_site__id=site.get('id')
                            )
                    site_transfer_apiary_site.customer_selected = checked_value
                    site_transfer_apiary_site.internal_selected = checked_value
                    site_transfer_apiary_site.save()

            #selected_licence = proposal_apiary_data.get('selected_licence')
            #if selected_licence:
            #    proposal_obj.proposal_apiary.target_approval = Approval.objects.get(id=selected_licence)
            #    proposal_obj.proposal_apiary.save()

            ## On submit, requirements need to be copied for originating and target approvals
            if viewset.action == 'submit':
                # set transferee for applications without a target licence
                #proposal_obj.proposal_apiary.transferee = EmailUser.objects.get(email=proposal_obj.proposal_apiary.transferee_email_text)
                #proposal_obj.proposal_apiary.save()
                # Find originating approval
                originating_approval = proposal_obj.proposal_apiary.retrieve_approval
                if originating_approval:
                    # Copy requirements from approval.current_proposal
                    #origin_req = originating_approval.current_proposal.apiary_requirements(
                     #       approval=originating_approval).exclude(is_deleted=True)
                    origin_req = originating_approval.proposalrequirement_set.exclude(is_deleted=True)
                    from copy import deepcopy
                    if origin_req:
                        for origin_r in origin_req:
                            old_origin_r = deepcopy(origin_r)
                            origin_r.proposal = proposal_obj
                            #origin_r.proposal = None
                            #origin_r.site_transfer_approval = originating_approval
                            #origin_r.apiary_approval = originating_approval
                            origin_r.apiary_approval = None
                            origin_r.sitetransfer_approval = originating_approval
                            origin_r.copied_from=old_origin_r
                            origin_r.id = None
                            origin_r.save()
                # Find target approval
                #approval = proposal_apiary.retrieve_approval
                if proposal_obj.proposal_apiary.target_approval:
                    # Copy requirements from approval.current_proposal
                    #target_req = proposal_obj.proposal_apiary.target_approval.current_proposal.apiary_requirements(
                     #       approval=proposal_obj.proposal_apiary.target_approval).exclude(is_deleted=True)
                    # origin_req = proposal_obj.proposal_apiary.target_approval.proposalrequirement_set.exclude(is_deleted=True)
                    target_req = proposal_obj.proposal_apiary.target_approval.proposalrequirement_set.exclude(is_deleted=True)
                    from copy import deepcopy
                    if target_req:
                        for target_r in target_req:
                            old_target_r = deepcopy(target_r)
                            target_r.proposal = proposal_obj
                            #target_r.apiary_approval = proposal_obj.proposal_apiary.target_approval
                            target_r.apiary_approval = None
                            target_r.sitetransfer_approval = proposal_obj.proposal_apiary.target_approval
                            target_r.copied_from=old_target_r
                            target_r.id = None
                            target_r.save()

            #proposal_obj.save()

        except Exception as e:
            raise


def save_proponent_data_apiary(proposal_obj, request, viewset):
    #import ipdb;ipdb.set_trace()
    with transaction.atomic():
        try:
            try:
                schema = request.data.get('schema')
            except:
                schema = request.POST.get('schema')

            sc = json.loads(schema) if schema else {}

            #save Site Locations data
            proposal_apiary_data = sc.get('proposal_apiary', None)

            if proposal_apiary_data:
                # New apairy site application
                local_date = get_local_date(proposal_apiary_data.get('public_liability_insurance_expiry_date', None), )
                proposal_apiary_data['public_liability_insurance_expiry_date'] = local_date.strftime('%Y-%m-%d') if local_date else None
                serializer = ProposalApiarySerializer(proposal_obj.proposal_apiary, data=proposal_apiary_data)
                serializer.is_valid(raise_exception=True)
                serializer.save()

                # site_locations_received = proposal_apiary_data['apiary_sites']
                site_locations_received = json.loads(request.data.get('all_the_features'))

                # Feature object doesn't have a field named 'id' originally unless manually added
                site_ids_received = []  # Store the apiary site ids already saved in the database
                for feature in site_locations_received:
                    if isinstance(feature['id_'], int):
                        site_ids_received.append(feature['id_'])
                    else:
                        try:
                            # feature['id_'] may have site_guid rather than database id even if it has been already saved.
                            # Because feature.id in the frontend is not updated until the page refreshed
                            site_already_saved = ApiarySite.objects.get(site_guid=feature['id_'])
                            site_ids_received.append(site_already_saved.id)
                        except:
                            pass
                # site_ids_existing = [site.id for site in ApiarySite.objects.filter(proposal_apiary_id=proposal_apiary_data['id'])]
                site_ids_existing = [site.id for site in proposal_obj.proposal_apiary.apiary_sites.all()]
                # site_ids_existing_vacant = [site.id for site in proposal_obj.proposal_apiary.vacant_apiary_sites.all()]
                site_ids_existing_vacant = []  # TODO implement
                site_ids_delete = [id for id in site_ids_existing if id not in site_ids_received]
                # site_ids_delete_vacant = [id for id in site_ids_existing_vacant if id not in site_ids_received] # TODO implement
                site_ids_delete_vacant = []

                # Handle ApiarySites here
                for index, feature in enumerate(site_locations_received):
                    feature['proposal_apiary_id'] = proposal_obj.proposal_apiary.id

                    try:
                        # Update existing
                        # for the newely addes apiary site, 'id_' has its guid
                        # for the existing apiary site, 'value_'.'site_guid' has its guid
                        try:
                            # Try to get this apiary site assuming already saved as 'draft'
                            a_site = ApiarySite.objects.get(site_guid=feature['id_'])

                        except ApiarySite.DoesNotExist:
                            # Try to get this apiary site assuming it is 'vacant' site (available site)
                            a_site = ApiarySite.objects.get(site_guid=feature['values_']['site_guid'])

                        serializer = ApiarySiteSerializer(a_site, data=feature)
                    except KeyError:  # when 'site_guid' is not defined above
                        # Create new apiary site when both of the above queries failed
                        # if feature['values_']['site_category'] == 'south_west':
                        #     category_obj = SiteCategory.objects.get(name='south_west')
                        # else:
                        #     category_obj = SiteCategory.objects.get(name='remote')
                        # feature['site_category_id'] = category_obj.id
                        feature['site_guid'] = feature['id_']

                        serializer = ApiarySiteSerializer(data=feature)
                        # This is test line for gitpush

                    if serializer:
                        serializer.is_valid(raise_exception=True)
                        apiary_site_obj = serializer.save()

                        # Save coordinate
                        geom_str = GEOSGeometry(
                            'POINT(' +
                            str(feature['values_']['geometry']['flatCoordinates'][0]) + ' ' +
                            str(feature['values_']['geometry']['flatCoordinates'][1]) +
                            ')', srid=4326
                        )
                        # Get apiary_site_on_proposal obj
                        apiary_site_on_proposal, created = ApiarySiteOnProposal.objects.get_or_create(apiary_site=apiary_site_obj, proposal_apiary=proposal_obj.proposal_apiary)
                        # Save the coordinate as 'draft' coordinate
                        serializer = ApiarySiteOnProposalDraftGeometrySaveSerializer(apiary_site_on_proposal, data={
                            'wkb_geometry_draft': geom_str,
                            # 'workflow_selected_status': False,
                        })
                        serializer.is_valid(raise_exception=True)
                        serializer.save()

                        if viewset.action == 'submit':
                            # When submit, copy the coordinates from draft to the processed
                            # apiary_site_on_proposal.wkb_geometry_processed = apiary_site_on_proposal.wkb_geometry_draft
                            # apiary_site_on_proposal.site_status = ApiarySiteOnProposal.SITE_STATUS_PENDING_PAYMENT
                            apiary_site_on_proposal.making_payment = True  # This should replace the above line.  site_status should not be overwritten by 'pending_payment'
                            apiary_site_on_proposal.save()

#                        if apiary_site_obj.status in (ApiarySite.STATUS_DRAFT, ApiarySite.STATUS_PENDING, ApiarySite.STATUS_VACANT, ApiarySite.STATUS_CURRENT,):
#                            data = {'wkb_geometry_pending': geom_str}
#                            save_point_serializer = ApiarySiteSavePointPendingSerializer
#                        else:
#                            # Should not reach here?
#                            pass
#                        serializer = save_point_serializer(apiary_site_obj, data=data)
#                        serializer.is_valid(raise_exception=True)
#                        serializer.save()

                        # if apiary_site_obj.is_vacant:
                        #     apiary_site_obj.proposal_apiary = None  # This should be already None
                        #     apiary_site_obj.proposal_apiaries.add(proposal_obj.proposal_apiary)
                        #     apiary_site_obj.save()

                if viewset.action == 'submit':
                    proposal_obj.proposal_apiary.validate_apiary_sites(raise_exception=True)

                save_checklist_answers('applicant', proposal_apiary_data.get('applicant_checklist_answers'))
                # expiry_date = sanitize_date(proposal_apiary_data.get('public_liability_insurance_expiry_date'))
                # proposal_obj.proposal_apiary.public_liability_insurance_expiry_date = expiry_date
                # proposal_obj.proposal_apiary.save()

                # Delete existing
                sites_delete = ApiarySite.objects.filter(id__in=site_ids_delete)
                for site_to_delete in sites_delete:
                    proposal_obj.proposal_apiary.delete_relation(site_to_delete)


                # sites_delete.delete()

                # Update the site(s) which is picked up as proposed site
                # sites_updated = ApiarySite.objects.filter(id__in=site_ids_delete)
                # sites_updated.update(proposal_apiary=None)

                # Delete association with 'vacant' site
                # sites_remove = ApiarySite.objects.filter(id__in=site_ids_delete_vacant, status=ApiarySite.STATUS_VACANT)
                # for vacant_site in sites_remove:
                #     vacant_site.proposal_apiaries.remove(proposal_obj.proposal_apiary)

            # Save Temporary Use data
            temporary_use_data = request.data.get('apiary_temporary_use', None)
            if temporary_use_data:
                # Temporary Use Application
                apiary_temporary_use_obj = ProposalApiaryTemporaryUse.objects.get(id=request.data.get('apiary_temporary_use')['id'])
                apiary_temporary_use_data = request.data.get('apiary_temporary_use')
                update_proposal_apiary_temporary_use(apiary_temporary_use_obj, apiary_temporary_use_data, viewset.action)

                if viewset.action == 'submit':
                    proposal_obj.processing_status = Proposal.PROCESSING_STATUS_WITH_ASSESSOR
                    proposal_obj.customer_status = Proposal.CUSTOMER_STATUS_WITH_ASSESSOR
                    proposal_obj.documents.all().update(can_delete=False)
                    #proposal.required_documents.all().update(can_delete=False)
                    proposal_obj.save()

                # return redirect(reverse('external-proposal-temporary-use-submit-success', kwargs={'proposal_pk': proposal_obj.id}))

            # save/update any additonal special propoerties here
            proposal_obj.title = proposal_obj.proposal_apiary.title if hasattr(proposal_obj, 'proposal_apiary') else proposal_obj.title
            proposal_obj.save()
        except Exception as e:
            raise


def get_local_date(date_string):
    if date_string:
        try:
            date_utc = datetime.strptime(date_string, '%Y-%m-%dT%H:%M:%S.%fZ')
        except:
            date_utc = datetime.strptime(date_string, '%Y-%m-%d')
        date_utc = date_utc.replace(tzinfo=pytz.UTC)
        date_wa = date_utc.astimezone(pytz.timezone(TIME_ZONE))
        return date_wa
    return None


def save_checklist_answers(checklist_role, checklist_answers=None):
    if checklist_answers and checklist_role == 'referrer':
        for referral_answers in checklist_answers:
            for ref_answer in referral_answers.get('referral_data'):
                r_ans = ApiaryChecklistAnswer.objects.get(id=ref_answer['id'])
                if ref_answer.get('question', {}).get('answer_type') == 'free_text':
                    #import ipdb; ipdb.set_trace()
                    r_ans.text_answer = ref_answer['text_answer']
                elif ref_answer.get('question', {}).get('answer_type') == 'yes_no':
                    r_ans.answer = ref_answer['answer']
                r_ans.save()
    #elif checklist_answers and checklist_role == 'assessor':
    else:
        for new_answer in checklist_answers:
            ans = ApiaryChecklistAnswer.objects.get(id=new_answer['id'])
            if new_answer.get('question', {}).get('answer_type') == 'free_text':
                ans.text_answer = new_answer['text_answer']
            elif new_answer.get('question', {}).get('answer_type') == 'yes_no':
                ans.answer = new_answer['answer']
            ans.save()


def update_proposal_apiary_temporary_use(temp_use_obj, temp_use_data, action):
    temp_use_data['from_date'] = convert_moment_str_to_python_datetime_obj(temp_use_data['from_date']).date() if temp_use_data['from_date'] else None
    temp_use_data['to_date'] = convert_moment_str_to_python_datetime_obj(temp_use_data['to_date']).date() if temp_use_data['to_date'] else None

    serializer = ProposalApiaryTemporaryUseSerializer(temp_use_obj, data=temp_use_data, context={'action': action})
    serializer.is_valid(raise_exception=True)
    patu = serializer.save()

    # Update TemporaryUseApiarySite
    num_of_sites = 0
    for item in temp_use_data['temporary_use_apiary_sites']:
        # Store all the apiary sites regardless of the selection status
        item['selected'] = item['apiary_site']['checked']
        tuas_obj = TemporaryUseApiarySite.objects.get(id=item['id'])

        serializer = TemporaryUseApiarySiteSerializer(tuas_obj, data=item)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Calculate the numbe of sites selected
        if item['selected']:
            num_of_sites += 1

    if action == 'submit':
        field_errors = {}
        non_field_errors = []

        for item in temp_use_data['temporary_use_apiary_sites']:
            if item['apiary_site']['checked']:
                # apiary_site = ApiarySite.objects.get(id=item['apiary_site']['id'])
                # valid, details = apiary_site.period_valid_for_temporary_use((temp_use_data['from_date'], temp_use_data['to_date']))
                valid, details = temp_use_obj.period_valid_for_temporary_use((temp_use_data['from_date'], temp_use_data['to_date']))
                if not valid:
                    if details['reason'] == 'overlap_existing':
                        non_field_errors.append('Temporary use period you submitted: {} to {} overlaps with the existing temporary use period: {} to {} for the apiary site: {}.'.format(
                            temp_use_data['from_date'], temp_use_data['to_date'], details['period']['from_date'], details['period']['to_date'], details['apiary_site'].id
                        ))
                        break
                    elif details['reason'] == 'out_of_range_of_licence':
                        non_field_errors.append('Temporary use period you submitted: {} to {} is out of range of the period of validity of the licence: {} to {}.'.format(
                            temp_use_data['from_date'], temp_use_data['to_date'], details['period']['from_date'], details['period']['to_date']
                        ))
                        break
                    else:
                        pass
                        # Should not reach here

        if not num_of_sites > 0:
            non_field_errors.append('At least one apiary site must be selected.')
        if not temp_use_obj.proposal.deed_poll_documents.all().count() > 0:
            non_field_errors.append('Deed poll document is required.')

        if field_errors:
            raise serializers.ValidationError(field_errors)
        if non_field_errors:
            raise serializers.ValidationError(non_field_errors)


    # if not temp_use_data['from_date']:
        #     non_field_errors.append('From date must be entered')
        # if not temp_use_data['to_date']:
        #     non_field_errors.append('To date must be entered')



def save_proponent_data_disturbance(instance,request,viewset):
    with transaction.atomic():
        try:
            lookable_fields = ['isTitleColumnForDashboard','isActivityColumnForDashboard','isRegionColumnForDashboard']

            extracted_fields,special_fields = create_data_from_form(instance.schema, request.POST, request.FILES, special_fields=lookable_fields)
            instance.data = extracted_fields
            #import ipdb; ipdb.set_trace()

            form_data=json.loads(request.POST['schema'])
            sub_activity_level1=form_data.get('sub_activity_level1')
            print(sub_activity_level1)

            logger.info("Region: {}, Activity: {}".format(special_fields.get('isRegionColumnForDashboard',None), special_fields.get('isActivityColumnForDashboard',None)))

            data1 = {
                #'region': special_fields.get('isRegionColumnForDashboard',None),
                'title': special_fields.get('isTitleColumnForDashboard',None),
                'activity': special_fields.get('isActivityColumnForDashboard',None),

                'data': extracted_fields,
                'processing_status': instance.PROCESSING_STATUS_CHOICES[1][0] if instance.processing_status == 'temp' else instance.processing_status,
                'customer_status': instance.PROCESSING_STATUS_CHOICES[1][0] if instance.processing_status == 'temp' else instance.customer_status,
                # 'lodgement_sequence': 1 if instance.lodgement_sequence == 0 else instance.lodgement_sequence,

            }
            data = {
                #'region': special_fields.get('isRegionColumnForDashboard',None),
                'title': special_fields.get('isTitleColumnForDashboard',None),

                'data': extracted_fields,
                'processing_status': instance.PROCESSING_STATUS_CHOICES[1][0] if instance.processing_status == 'temp' else instance.processing_status,
                'customer_status': instance.PROCESSING_STATUS_CHOICES[1][0] if instance.processing_status == 'temp' else instance.customer_status,
                # 'lodgement_sequence': 1 if instance.lodgement_sequence == 0 else instance.lodgement_sequence,
                'activity': form_data.get('activity',None),
                'region': form_data.get('region',None),
                'district': form_data.get('district',None),
                'sub_activity_level1': form_data.get('sub_activity_level1',None),
                'sub_activity_level2': form_data.get('sub_activity_level2',None),
                'management_area': form_data.get('management_area',None),
                'approval_level': form_data.get('approval_level',None),

            }

            serializer = SaveProposalSerializer(instance, data, partial=True)
            serializer.is_valid(raise_exception=True)
            viewset.perform_update(serializer)
            instance.log_user_action(ProposalUserAction.ACTION_SAVE_APPLICATION.format(instance.lodgement_number), request)

            # Save Documents
        #            for f in request.FILES:
        #                try:
        #                    #document = instance.documents.get(name=str(request.FILES[f]))
        #                    document = instance.documents.get(input_name=f)
        #                except ProposalDocument.DoesNotExist:
        #                    document = instance.documents.get_or_create(input_name=f)[0]
        #                document.name = str(request.FILES[f])
        #                if document._file and os.path.isfile(document._file.path):
        #                    os.remove(document._file.path)
        #                document._file = request.FILES[f]
        #                document.save()

        #            for f in request.FILES:
        #                #import ipdb; ipdb; ipdb.set_trace()
        #                try:
        #                   document = instance.documents.get(input_name=f, name=request.FILES[f].name)
        #                except ProposalDocument.DoesNotExist:
        #                   document = instance.documents.get_or_create(input_name=f, name=request.FILES[f].name)[0]
        #                document._file = request.FILES[f]
        #                document.save()

        # End Save Documents
        except:
            raise


def save_assessor_data(instance,request,viewset):
    with transaction.atomic():
        try:
            lookable_fields = ['isTitleColumnForDashboard','isActivityColumnForDashboard','isRegionColumnForDashboard']
            extracted_fields,special_fields,assessor_data,comment_data = create_data_from_form(
                instance.schema, request.POST, request.FILES,special_fields=lookable_fields,assessor_data=True)

            logger.info("ASSESSOR DATA - Region: {}, Activity: {}".format(special_fields.get('isRegionColumnForDashboard',None), special_fields.get('isActivityColumnForDashboard',None)))

            data = {
                'data': extracted_fields,
                'assessor_data': assessor_data,
                'comment_data': comment_data,
            }
            serializer = SaveProposalSerializer(instance, data, partial=True)
            serializer.is_valid(raise_exception=True)
            viewset.perform_update(serializer)
            # Save Documents
            for f in request.FILES:
                try:
                    #document = instance.documents.get(name=str(request.FILES[f]))
                    document = instance.documents.get(input_name=f)
                except ProposalDocument.DoesNotExist:
                    document = instance.documents.get_or_create(input_name=f)[0]
                document.name = str(request.FILES[f])
                if document._file and os.path.isfile(document._file.path):
                    os.remove(document._file.path)
                document._file = request.FILES[f]
                document.save()
            # End Save Documents
            instance.log_user_action(ProposalUserAction.ACTION_SAVE_APPLICATION.format(instance.lodgement_number), request)
        except:
            raise


def save_apiary_assessor_data(instance,request,viewset):
    with transaction.atomic():
        try:
            #import ipdb; ipdb.set_trace()
            serializer = SaveProposalSerializer(instance, request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            viewset.perform_update(serializer)
            # Save Documents
            for f in request.FILES:
                try:
                    #document = instance.documents.get(name=str(request.FILES[f]))
                    document = instance.documents.get(input_name=f)
                except ProposalDocument.DoesNotExist:
                    document = instance.documents.get_or_create(input_name=f)[0]
                document.name = str(request.FILES[f])
                if document._file and os.path.isfile(document._file.path):
                    os.remove(document._file.path)
                document._file = request.FILES[f]
                document.save()
            # End Save Documents
            # save assessor checklist answers
            try:
                schema = request.data.get('schema')
            except:
                schema = request.POST.get('schema')

            sc = json.loads(schema) if schema else {}

            proposal_apiary_data = sc.get('proposal_apiary')
            if proposal_apiary_data:
                save_checklist_answers('assessor', proposal_apiary_data.get('assessor_checklist_answers'))
                save_checklist_answers('assessor', proposal_apiary_data.get('assessor_checklist_answers_per_site'))
                save_checklist_answers('assessor', proposal_apiary_data.get('site_transfer_assessor_checklist_answers'))
                save_checklist_answers('assessor', proposal_apiary_data.get('site_transfer_assessor_checklist_answers_per_site'))
            # referrer checklist answers
            try:
                referrer_checklist_answers_str = request.data.get('referrer_checklist_answers')
            except:
                referrer_checklist_answers_str = request.POST.get('referrer_checklist_answers')
            referrer_checklist_answers = json.loads(referrer_checklist_answers_str) if referrer_checklist_answers_str else []
            if referrer_checklist_answers:
                save_checklist_answers('referrer', referrer_checklist_answers)
            # referrer checklist answers per site
            try:
                referrer_checklist_answers_per_site_str = request.data.get('referrer_checklist_answers_per_site')
            except:
                referrer_checklist_answers_per_site_str = request.POST.get('referrer_checklist_answers_per_site')
            referrer_checklist_answers_per_site = json.loads(referrer_checklist_answers_per_site_str) if referrer_checklist_answers_per_site_str else []
            if referrer_checklist_answers_per_site:
                save_checklist_answers('referrer', referrer_checklist_answers_per_site)
            # site transfer referrer checklist answers
            try:
                site_transfer_referrer_checklist_answers_str = request.data.get('site_transfer_referrer_checklist_answers')
            except:
                site_transfer_referrer_checklist_answers_str = request.POST.get('site_transfer_referrer_checklist_answers')
            site_transfer_referrer_checklist_answers = json.loads(referrer_checklist_answers_str) if referrer_checklist_answers_str else []
            if site_transfer_referrer_checklist_answers:
                save_checklist_answers('referrer', site_transfer_referrer_checklist_answers)
            # site transfer referrer checklist answers per site
            try:
                site_transfer_referrer_checklist_answers_per_site_str = request.data.get('site_transfer_referrer_checklist_answers_per_site')
            except:
                site_transfer_referrer_checklist_answers_per_site_str = request.POST.get('site_transfer_referrer_checklist_answers_per_site')
            site_transfer_referrer_checklist_answers_per_site = json.loads(referrer_checklist_answers_per_site_str) if referrer_checklist_answers_per_site_str else []
            if site_transfer_referrer_checklist_answers_per_site:
                save_checklist_answers('referrer', site_transfer_referrer_checklist_answers_per_site)

            instance.log_user_action(ProposalUserAction.APIARY_ACTION_SAVE_APPLICATION.format(instance.lodgement_number), request)
        except:
            raise

def proposal_submit_apiary(proposal, request):
    with transaction.atomic():
        if proposal.can_user_edit:
            proposal.submitter = request.user
            #proposal.lodgement_date = datetime.datetime.strptime(timezone.now().strftime('%Y-%m-%d'),'%Y-%m-%d').date()
            proposal.lodgement_date = timezone.now()
            proposal.training_completed = True
            if (proposal.amendment_requests):
                qs = proposal.amendment_requests.filter(status = "requested")
                if (qs):
                    for q in qs:
                        q.status = 'amended'
                        q.save()

            # Create a log entry for the proposal
            proposal.log_user_action(ProposalUserAction.ACTION_LODGE_APPLICATION.format(proposal.lodgement_number), request)
            # Create a log entry for the organisation
            #proposal.applicant.log_user_action(ProposalUserAction.ACTION_LODGE_APPLICATION.format(proposal.id),request)
            applicant_field=getattr(proposal, proposal.applicant_field)
            applicant_field.log_user_action(ProposalUserAction.ACTION_LODGE_APPLICATION.format(proposal.lodgement_number), request)

            ret1 = send_submit_email_notification(request, proposal)
            ret2 = send_external_submit_email_notification(request, proposal)

            #proposal.save_form_tabs(request)
            if ret1 and ret2:
                proposal.processing_status = Proposal.PROCESSING_STATUS_WITH_ASSESSOR
                proposal.customer_status = Proposal.CUSTOMER_STATUS_WITH_ASSESSOR
                proposal.documents.all().update(can_delete=False)
                #proposal.required_documents.all().update(can_delete=False)
                proposal.save()
            else:
                raise ValidationError('An error occurred while submitting proposal (Submit email notifications failed)')

            #import ipdb; ipdb.set_trace()
            if proposal.application_type.name == 'Apiary':
                for question in ApiaryChecklistQuestion.objects.filter(
                        checklist_type='apiary',
                        checklist_role='assessor'
                        ):
                    new_answer = ApiaryChecklistAnswer.objects.create(proposal = proposal.proposal_apiary,
                                                                               question = question)
                # add questions per site
                for question in ApiaryChecklistQuestion.objects.filter(
                        checklist_type='apiary_per_site',
                        checklist_role='assessor'
                        ):
                    # site is an ApiarySiteOnProposal obj
                    for site in proposal.proposal_apiary.get_relations():
                        new_answer = ApiaryChecklistAnswer.objects.create(proposal = proposal.proposal_apiary,
                                                                                   question = question,
                                                                                   apiary_site=site.apiary_site)
            elif proposal.application_type.name == 'Site Transfer':
                for question in ApiaryChecklistQuestion.objects.filter(
                        checklist_type='site_transfer',
                        checklist_role='assessor'
                        ):
                    new_answer = ApiaryChecklistAnswer.objects.create(proposal = proposal.proposal_apiary,
                                                                               question = question)
                #import ipdb; ipdb.set_trace()
                # add questions per site
                for question in ApiaryChecklistQuestion.objects.filter(
                        checklist_type='site_transfer_per_site',
                        checklist_role='assessor'
                        ):
                    # site is an ApiarySiteOnApproval obj
                    for site in proposal.proposal_apiary.get_relations():
                        new_answer = ApiaryChecklistAnswer.objects.create(proposal = proposal.proposal_apiary,
                                                                                   question = question,
                                                                                   apiary_site=site.apiary_site)

            return proposal

        else:
            raise ValidationError('You can\'t edit this proposal at this moment')


def clone_proposal_with_status_reset(proposal):
    with transaction.atomic():
        try:
            proposal.customer_status = 'draft'
            proposal.processing_status = 'draft'
            proposal.assessor_data = {}
            proposal.comment_data = {}

            #proposal.id_check_status = 'not_checked'
            #proposal.character_check_status = 'not_checked'
            #proposal.compliance_check_status = 'not_checked'
            #Sproposal.review_status = 'not_reviewed'

            proposal.lodgement_number = ''
            proposal.lodgement_sequence = 0
            proposal.lodgement_date = None

            proposal.assigned_officer = None
            proposal.assigned_approver = None

            proposal.approval = None

            original_proposal_id = proposal.id

            proposal.previous_proposal = proposal.objects.get(id=original_proposal_id)

            proposal.id = None

            #proposal.save(no_revision=True)
            proposal.save()


            # clone documents
            for proposal_document in ProposalDocument.objects.filter(proposal=original_proposal_id):
                proposal_document.proposal = proposal
                proposal_document.id = None
                proposal_document.save()

            return proposal
        except:
            raise

def get_options(question):
    options=[]
    if question.option.count()>0:
        for op in question.option.all():
            op_dict={
                'label': op.label,
                'value': op.value
            }
            options.append(op_dict)
    return options

def get_condition_chidren(question,section):
    conditions={}
    options=question.option.all()
    for op in options:
        condition_questions=SectionQuestion.objects.filter(section=section,parent_question=question,parent_answer=op)
        if condition_questions:
            option_section=[]
            option_children=[]
            for q in condition_questions:
                child={
                    'name': q.question.name,
                    'type:': q.question.answer_type,
                    'label': q.question.question,
                }
                if q.question.option.count()>0:
                    q_options= get_options(q.question)
                    child['options']=q_options
                if q.question.children_question.exists():
                    q_conditions=get_condition_chidren(q.question, section)
                    child['conditions']=q_conditions
                if q.tag:
                    for t in q.tag:
                        child[t]='true'
                if q.question.help_text_url:
                    child['_help_text_url']=q.question.help_text_url
                if q.question.help_text_assessor_url:
                    child['_help_text_assessor_url']=q.question.help_text_assessor_url
                option_children.append(child)
            section_group_name=section.section_name+'-'+op.label+'Group'
            option_section_dict={
                'name':section_group_name,
                'type': 'group',
                'label':'',
                'children': option_children
            }
            option_section.append(option_section_dict)
            conditions[op.value]=option_section
    return conditions





def generate_schema(proposal_type):
    section_list=ProposalTypeSection.objects.filter(proposal_type=proposal_type).order_by('index')
    count=0
    schema=[]
    for section in section_list:
        section_dict={
            'name': section.section_name,
            'type': 'section',
            'label': section.section_label,
        }
        section_children=[]
        section_questions=SectionQuestion.objects.filter(section=section,parent_question__isnull=True,parent_answer__isnull=True)
        if section_questions:
            for sq in section_questions:
                sc={
                    'name': sq.question.name,
                    'type': sq.question.answer_type,
                    'label': sq.question.question,                    
                }
                if sq.question.option.count()>0:
                    sq_options= get_options(sq.question)
                    sc['options']=sq_options
                if sq.question.children_question.exists():
                    sq_children=get_condition_chidren(sq.question,section)
                    sc['conditions']=sq_children
                    # sc['conditions']=[{'child':'yes'}]
                if sq.tag:
                    for t in sq.tag:
                        sc[t]='true'
                if sq.question.help_text_url:
                    sc['_help_text_url']=sq.question.help_text_url
                if sq.question.help_text_assessor_url:
                    sc['_help_text_assessor_url']=sq.question.help_text_assessor_url
                section_children.append(sc)
        if section_children:
            section_dict['children']= section_children
        schema.append(section_dict)
    import json
    new_schema=json.dumps(schema)
    return new_schema


                