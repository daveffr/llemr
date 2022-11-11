import datetime
import json
from django.views.generic import TemplateView
from django.http import JsonResponse
from osler.core.models import Encounter
from osler.demographics.models import Demographics
from osler.inventory.models import DispenseHistory
from osler.labs.models import Lab
from osler.users.decorators import active_permission_required
from osler.workup.models import Workup
from django.utils.decorators import method_decorator


homeless_address = '3151 Olive St.'
ethnicity_list = []
zip_code_list = []
@method_decorator(active_permission_required('users.view_clinic_datadashboard', raise_exception=True), name='dispatch')
class DataDashboardView(TemplateView):
    template_name = 'datadashboard/data_dashboard.html'        


def send_patientdata_json(request):
    '''Sends patient and workup related data to be used in main dashboard data charts'''
    all_workups = query_workups_model()
    all_demographics = query_demographics_model()
    all_drugs_dispensed = query_drug_model()
    all_labs_ordered = query_labs_model()

    dashboard_data = format_patient_data(all_workups, all_demographics, all_drugs_dispensed, all_labs_ordered)
    return JsonResponse(dashboard_data)

def query_workups_model():
    '''Queries all workups and extracts demographic data'''
    return Workup.objects.all().\
        select_related('patient').\
        select_related('patient__gender').\
        prefetch_related('patient__ethnicities')

def query_demographics_model():
    """ Reformats all Demographic data for json by processing into a python dictoinary"""
    raw_demographics = Demographics.objects.all()
    formatted_demographics = {}
    for demographic in raw_demographics:
        demo_data = {}
        conditions = []
        for condition in list(demographic.chronic_conditions.all()):
                conditions.append(getattr(condition, 'name'))
        demo_data["conditions"] = conditions
        demo_data["has_insurance"] = demographic.has_insurance

        # need to check if an annual income has been specified, skip over this if not
        if demographic.annual_income is not None:
            demo_data["income_range"] = demographic.annual_income.name
        formatted_demographics[demographic.pk] = demo_data
    
    # formatted_demographics maps the primary key of each demographic to its data
    # the data is formatted for easier use with json
    return formatted_demographics


def query_drug_model():
    '''Queries inventory and extracts dispense history models organized by patient'''
    drug_dispenses_by_pt = {}
    dispenses = DispenseHistory.objects.all()

    for item in dispenses:
        written_date = datetime.datetime.strftime(getattr(item, "written_datetime"), "%Y-%m-%d")
        drug = getattr(item, "drug")
        drug_name = getattr(drug, "name")
        drug_encounter = getattr(item, "encounter")
        drug_patient = getattr(drug_encounter, "patient")
        drug_patient_pk = getattr(drug_patient, "pk")      

        # check if the patient at hand is already in drug_dispenses_by_pt and initialize a dictionary for them if not
        if(drug_patient_pk not in drug_dispenses_by_pt):
          drug_dispenses_by_pt[drug_patient_pk] = {}
        
        # if this is the first instance of the drug being dispensed, make a new list contianing its dispense date, else add it to already existing list
        if(drug_name not in drug_dispenses_by_pt[drug_patient_pk]):
          drug_dispenses_by_pt[drug_patient_pk][drug_name] = [written_date]
        else:
          drug_dispenses_by_pt[drug_patient_pk][drug_name].append(written_date)

    # drug_dispenses_by_pt is a dictionary that maps each patient's primary key to a dictionary
    # that maps each drug the patient has taken to a list of dates of each time the drug in question 
    # was dispensed to them     
    return drug_dispenses_by_pt


def query_labs_model():
    '''Queries all labs and formats their written dates into a 2d dictionary 
    organized by patient at the top level and lab type at the second level'''
    labs_by_patient = {}
    labs = Lab.objects.all()
    for lab in labs:
        written_date = datetime.datetime.strftime(getattr(lab, "lab_time"), "%Y-%m-%d")
        lab_type = getattr(lab, "lab_type")
        lab_type_name = getattr(lab_type, "name")
        lab_patient = getattr(lab,"patient")
        lab_patient_pk = getattr(lab_patient, "pk")

        if(lab_patient_pk not in labs_by_patient):
          labs_by_patient[lab_patient_pk] = {} 
        
        if(lab_type_name not in labs_by_patient[lab_patient_pk]):
          labs_by_patient[lab_patient_pk][lab_type_name] = [written_date]
        else:
          labs_by_patient[lab_patient_pk][lab_type_name].append(written_date)
    
    # labs_by_patient is a dictionary that maps each patient's primary key to a dictionary
    # that maps each lab the patient was involved with to the date(s) they were involced 
    return labs_by_patient


def get_ethnicities(wu):
    ethnicities = []
    for ethnicity in list(wu.patient.ethnicities.all()):
        # add to list of all ethnicities if we haven't seen this ethnicity yet
        if(ethnicity not in ethnicity_list):
            ethnicity_list.append(ethnicity)
        ethnicities.append(getattr(ethnicity, 'name'))
    return ethnicities


def get_zip_code(wu):
    # add to list of all zip codes if we haven't seen this zip code yet
    if(wu.patient.zip_code not in zip_code_list):
        zip_code_list.append(wu.patient.zip_code)

    if(wu.patient.address != homeless_address):
        return wu.patient.zip_code
    else:
        return None


def gather_data_for_patient(wu, demo, drugs, labs, pk):
    """
    Gathers all data in demo, drugs, and labs corresponding to the patient with the primary key pk
    """
    patient_data = {}
    patient_data['age'] = (wu.encounter.clinic_day - wu.patient.date_of_birth).days // 365
    patient_data['gender'] = wu.patient.gender.name
    patient_data['name'] = wu.patient.name()
    patient_data['wu_dates'] = [str(wu.encounter.clinic_day)]
    patient_data['ethnicities'] = get_ethnicities(wu)
    patient_data['zip_code'] = get_zip_code(wu)

    if(pk in demo):
        patient_data['conditions'] = demo[pk]['conditions']
        patient_data['has_insurance'] = demo[pk]['has_insurance']
        if 'income_range' in demo[pk].keys():
            patient_data['income_range'] = demo[pk]['income_range']
    else:
        patient_data['conditions'] = []

    if(pk in drugs):
        patient_data['drugs'] = drugs[pk]
    else:
        patient_data['drugs'] = None

    if(pk in labs):
        patient_data['labs'] = labs[pk]
    else:
        patient_data['labs'] = None

    return patient_data


def format_patient_data(workups,demo,drugs,labs):
    '''takes in queryed workups then extracts and formats related demographic data into json friendly formating
    '''
    dashboard_data = {}
    unique_patient_pk_list = []
    for wu in workups:
        pk = wu.patient.pk
        # check if we haven't seen current patient before. If so, add patient primary keys to list of unique primary keys and gather data
        if pk not in unique_patient_pk_list:
            unique_patient_pk_list.append(pk)
            patient_data = gather_data_for_patient(wu, demo, drugs, labs, pk)
            dashboard_data[pk] = patient_data
        else: 
            # if we have seen current patient already, adds repeat workups to date list to be used in js side date filtering
            existing_wu_dates = dashboard_data.get(pk)['wu_dates']
            existing_wu_dates.append(str(wu.encounter.clinic_day))

    return dashboard_data


def send_context_json(request):
    ''' Formats context data such as clinic dates for json '''
    context = {}
    context["num_ethnicities"] = len(ethnicity_list)
    context["num_zipcodes"] = len(zip_code_list)
    context["clinic_dates"] = json.dumps(list_clinic_dates())
    return JsonResponse(context)

def list_clinic_dates():
    '''Queries all Encounters and filters them into a date ordered list of unique dates in which patients were seen
    serves as a proxy to the old ClinicDate model
    '''
    raw_encounters = Encounter.objects.all()
    dates = []
    # turn each encounter date into a date string and append to the list of dates
    for encounter in raw_encounters:
        date = datetime.datetime.strftime(getattr(encounter, "clinic_day"), "%Y-%m-%d")
        if date not in dates:
          dates.append(date)
    dates.sort()
    return dates


