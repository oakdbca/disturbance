from ledger.accounts.models import EmailUser
from rest_framework import serializers
from rest_framework_gis.serializers import GeoFeatureModelSerializer

from disturbance.components.approvals.models import ApiarySiteOnApproval
from disturbance.components.main.utils import get_category, get_tenure, get_region_district, get_status_for_export
from disturbance.components.organisations.models import Organisation


class ApiarySiteOnApprovalMinimalGeometrySerializer(GeoFeatureModelSerializer):
    id = serializers.IntegerField(source='apiary_site__id')
    status = serializers.CharField(source='site_status')
    site_category = serializers.CharField(source='site_category__name')
    is_vacant = serializers.BooleanField(source='apiary_site__is_vacant')
    site_guid = serializers.CharField(source='apiary_site__site_guid')
    #licensed_site = serializers.BooleanField(source='apiary_site__licensed_site')
    lodgement_number = serializers.CharField(source='approval__lodgement_number')
    approval_id = serializers.IntegerField(source='approval__id')

    class Meta:
        model = ApiarySiteOnApproval
        geo_field = 'wkb_geometry'
        fields = (
            'id',
            'is_vacant',
            'wkb_geometry',
            'site_category',
            'status',
            'site_guid',
            'available',
            'lodgement_number',
            'approval_id',
            # 'licensed_site',
            # 'batch_no',
            # 'approval_cpc_date',
            # 'approval_minister_date',
            # 'map_ref',
            # 'forest_block',
            # 'cog',
            # 'roadtrack',
            # 'zone',
            # 'catchment',
            # 'dra_permit',
        )


class ApiarySiteOnApprovalMinGeometrySerializer(GeoFeatureModelSerializer):
    """
    For reading
    """
    id = serializers.IntegerField(source='apiary_site.id')
    site_guid = serializers.CharField(source='apiary_site.site_guid')
    status = serializers.CharField(source='site_status')
    site_category = serializers.CharField(source='site_category.name')
    previous_site_holder_or_applicant = serializers.SerializerMethodField()
    is_vacant = serializers.BooleanField(source='apiary_site.is_vacant')
    stable_coords = serializers.SerializerMethodField()
    approval_lodgement_number = serializers.CharField(source='approval.lodgement_number')

    class Meta:
        model = ApiarySiteOnApproval
        geo_field = 'wkb_geometry'
        fields = (
            'id',
            'site_guid',
            'available',
            'wkb_geometry',
            'site_category',
            'status',
            'is_vacant',
            'stable_coords',
            'previous_site_holder_or_applicant',
            'approval_lodgement_number',
        )

    def get_stable_coords(self, obj):
        return obj.wkb_geometry.get_coords()

    def get_previous_site_holder_or_applicant(self, obj):
        try:
            relevant_applicant_name = obj.approval.relevant_applicant_name
            return relevant_applicant_name
        except:
            return ''


class ApiarySiteOnApprovalGeometrySerializer(GeoFeatureModelSerializer):
    """
    For reading
    """
    id = serializers.IntegerField(source='apiary_site.id')
    site_guid = serializers.CharField(source='apiary_site.site_guid')
    status = serializers.CharField(source='site_status')
    site_category = serializers.CharField(source='site_category.name')
    previous_site_holder_or_applicant = serializers.SerializerMethodField()
    is_vacant = serializers.BooleanField(source='apiary_site.is_vacant')
    stable_coords = serializers.SerializerMethodField()
    #licensed_site = serializers.BooleanField(source='apiary_site.licensed_site')

    class Meta:
        model = ApiarySiteOnApproval
        geo_field = 'wkb_geometry'
        fields = (
            'id',
            'site_guid',
            'available',
            'wkb_geometry',
            'site_category',
            'status',
            'is_vacant',
            'stable_coords',
            'previous_site_holder_or_applicant',
            'licensed_site',
            'batch_no',
            'approval_cpc_date',
            'approval_minister_date',
            'map_ref',
            'forest_block',
            'cog',
            'roadtrack',
            'zone',
            'catchment',
            'dra_permit',
        )

    def get_stable_coords(self, obj):
        return obj.wkb_geometry.get_coords()

    def get_previous_site_holder_or_applicant(self, obj):
        try:
            relevant_applicant_name = obj.approval.relevant_applicant_name
            return relevant_applicant_name
        except:
            return ''


class ApiarySiteOnApprovalGeometryExportSerializer(ApiarySiteOnApprovalGeometrySerializer):
    site_id = serializers.IntegerField(source='apiary_site.id')
    status = serializers.SerializerMethodField()
    category = serializers.CharField(source='site_category.name')
    surname = serializers.SerializerMethodField()
    first_name = serializers.SerializerMethodField()
    address = serializers.SerializerMethodField()
    telephone = serializers.SerializerMethodField()
    mobile = serializers.SerializerMethodField()
    email = serializers.SerializerMethodField()
    organisation_name = serializers.SerializerMethodField()
    approval_lodgement_number = serializers.CharField(source='approval.lodgement_number')
    proposal_lodgement_number = serializers.SerializerMethodField()

    class Meta(ApiarySiteOnApprovalGeometrySerializer.Meta):
        fields = (
            'id',
            'site_id',
            'status',
            'category',
            'surname',
            'first_name',
            'address',
            'telephone',
            'mobile',
            'email',
            'organisation_name',
            'approval_lodgement_number',
            'proposal_lodgement_number',
        )

    def get_proposal_lodgement_number(self, obj):
        return ''

    def get_organisation_name(self, relation):
        relevant_applicant = relation.approval.relevant_applicant
        if isinstance(relevant_applicant, Organisation):
            return relevant_applicant.organisation.name
        else:
            return ''

    def get_status(self, relation):
        return get_status_for_export(relation)

    # def get_category(self, relation):
    #     return relation.site_category.name

    def get_surname(self, relation):
        relevant_applicant = relation.approval.relevant_applicant
        if isinstance(relevant_applicant, EmailUser):
            return relevant_applicant.last_name
        else:
            return ''

    def get_first_name(self, relation):
        relevant_applicant = relation.approval.relevant_applicant
        if isinstance(relevant_applicant, EmailUser):
            return relevant_applicant.first_name
        else:
            return ''

    def get_address(self, relation):
        try:
            address = relation.approval.relevant_applicant_address
            return address.summary
        except:
            return ''

    def get_telephone(self, relation):
        relevant_applicant = relation.approval.relevant_applicant
        if isinstance(relevant_applicant, EmailUser):
            return relevant_applicant.phone_number
        else:
            return ''

    def get_mobile(self, relation):
        relevant_applicant = relation.approval.relevant_applicant
        if isinstance(relevant_applicant, EmailUser):
            return relevant_applicant.phone_number
        else:
            return ''

    def get_email(self, relation):
        return relation.approval.relevant_applicant_email


class ApiarySiteOnApprovalLicenceDocSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='apiary_site.id')
    # site_category = serializers.CharField(source='site_category.name')
    site_category = serializers.SerializerMethodField()
    coords = serializers.SerializerMethodField()
    tenure = serializers.SerializerMethodField()
    region_district = serializers.SerializerMethodField()
    licensed_site = serializers.SerializerMethodField()
    batch_no = serializers.SerializerMethodField()
    approval_cpc_date = serializers.SerializerMethodField()
    approval_minister_date = serializers.SerializerMethodField()
    map_ref = serializers.SerializerMethodField()
    forest_block = serializers.SerializerMethodField()
    cog = serializers.SerializerMethodField()
    roadtrack = serializers.SerializerMethodField()
    zone = serializers.SerializerMethodField()
    catchment = serializers.SerializerMethodField()
    dra_permit = serializers.SerializerMethodField()
    fee_application = serializers.SerializerMethodField()
    fee_renewal = serializers.SerializerMethodField()
    fee_transfer = serializers.SerializerMethodField()

    class Meta:
        model = ApiarySiteOnApproval

        fields = (
            'id',
            'coords',
            'site_category',
            'tenure',
            'region_district',
            'licensed_site',
            'batch_no',
            'approval_cpc_date',
            'approval_minister_date',
            'map_ref',
            'forest_block',
            'cog',
            'roadtrack',
            'zone',
            'catchment',
            'dra_permit',
            'fee_application',
            'fee_renewal',
            'fee_transfer',


        )

    def get_site_category(self, apiary_site_on_approval):
        site_category = apiary_site_on_approval.site_category
        return site_category.display_name

    def get_tenure(self, apiary_site_on_approval):
        try:
            res = get_tenure(apiary_site_on_approval.wkb_geometry)
            return res
        except:
            return ''

    def get_region_district(self, apiary_site_on_approval):
        try:
            res = get_region_district(apiary_site_on_approval.wkb_geometry)
            return res
        except:
            return ''

    def get_coords(self, apiary_site_on_approval):
        try:
            # geometry_condition = self.context.get('geometry_condition', ApiarySite.GEOMETRY_CONDITION_APPROVED)
            # if geometry_condition == ApiarySite.GEOMETRY_CONDITION_APPLIED:
            #     return {'lng': apiary_site.wkb_geometry_applied.x, 'lat': apiary_site.wkb_geometry_applied.y}
            # elif geometry_condition == ApiarySite.GEOMETRY_CONDITION_PENDING:
            #     return {'lng': apiary_site.wkb_geometry_pending.x, 'lat': apiary_site.wkb_geometry_pending.y}
            # else:
            #     return {'lng': apiary_site.wkb_geometry.x, 'lat': apiary_site.wkb_geometry.y}
            return {'lng': apiary_site_on_approval.wkb_geometry.x, 'lat': apiary_site_on_approval.wkb_geometry.y}
        except:
            return {'lng': '', 'lat': ''}

    def get_licensed_site(self, apiary_site_on_proposal):
        try:
            return apiary_site_on_proposal.licensed_site
        except:
            return ''

    def get_batch_no(self, apiary_site_on_proposal):
        return apiary_site_on_proposal.batch_no if apiary_site_on_proposal.batch_no else ''

    def get_approval_cpc_date(self, apiary_site_on_proposal):
        return apiary_site_on_proposal.approval_cpc_date if apiary_site_on_proposal.approval_cpc_date else ''

    def get_approval_minister_date(self, apiary_site_on_proposal):
        return apiary_site_on_proposal.approval_minister_date if apiary_site_on_proposal.approval_minister_date else ''

    def get_map_ref(self, apiary_site_on_proposal):
        return apiary_site_on_proposal.map_ref if apiary_site_on_proposal.map_ref else ''

    def get_forest_block(self, apiary_site_on_proposal):
        return apiary_site_on_proposal.forest_block if apiary_site_on_proposal.forest_block else ''

    def get_cog(self, apiary_site_on_proposal):
        return apiary_site_on_proposal.cog if apiary_site_on_proposal.cog else ''

    def get_roadtrack(self, apiary_site_on_proposal):
        return apiary_site_on_proposal.roadtrack if apiary_site_on_proposal.roadtrack else ''

    def get_zone(self, apiary_site_on_proposal):
        return apiary_site_on_proposal.zone if apiary_site_on_proposal.zone else ''

    def get_catchment(self, apiary_site_on_proposal):
        return apiary_site_on_proposal.catchment if apiary_site_on_proposal.catchment else ''

    def get_dra_permit(self, apiary_site_on_proposal):
        return 'Yes' if apiary_site_on_proposal.dra_permit else 'No'

    def get_fee_application(self, apiary_site_on_approval):
        return apiary_site_on_approval.site_category.fee_application_per_site

    def get_fee_renewal(self, apiary_site_on_approval):
        return apiary_site_on_approval.site_category.fee_renewal_per_site

    def get_fee_transfer(self, apiary_site_on_approval):
        return apiary_site_on_approval.site_category.fee_transfer_per_site


