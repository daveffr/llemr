import datetime
import json
from django.utils.timezone import now
from django.views.generic import TemplateView
from django.http import JsonResponse
from osler.workup.models import Workup
from osler.datadashboard import models
from django.http import HttpResponseRedirect, HttpResponseNotFound, HttpResponse

class DataDashboardView(TemplateView):
    template_name = 'datadashboard/patient_data_dashboard.html'        

# def query_hypertension_workups():
#     '''Queries all workups defined as hypertensive (currently defined as bp_sys > 100)'''
#     hypertensive_workups = Workup.objects.filter(diagnosis__contains='hypertension').\
#         select_related('patient').\
#         select_related('patient__gender').\
#         prefetch_related('patient__ethnicities')
#     return hypertensive_workups

# def query_diabetes_workups():
#     '''Queries all workups defined as diabetic under diagnosis field'''
#     diabetic_workups = Workup.objects.filter(diagnosis__contains='diabetes').\
#         select_related('patient').\
#         select_related('patient__gender').\
#         prefetch_related('patient__ethnicities')
#     return diabetic_workups

def query_all_workups():
    '''Queries all workups'''
    return Workup.objects.all().\
        select_related('patient').\
        select_related('patient__gender').\
        prefetch_related('patient__ethnicities')
    

def extract_demographic_data(workups):
    '''takes in queryed workups then extracts and formats related demographic data into json friendly format'''
    dashboard_data = {}
    unique_patient_pk_list = []
    for wu in workups:
        demographics = {}
        if wu.patient.pk not in unique_patient_pk_list:
            unique_patient_pk_list.append(wu.patient.pk)
            demographics['conditions'] = wu.diagnosis
            demographics['age'] = (now().date() - wu.patient.date_of_birth).days // 365
            demographics['gender'] = wu.patient.gender.name
            ethnicities = []
            for ethnicity in list(wu.patient.ethnicities.all()):
                ethnicities.append(getattr(ethnicity, 'name'))
            demographics['ethnicities'] = ethnicities
            demographics['name'] = wu.patient.name()
            demographics['wu_dates'] = [str(wu.written_datetime.date())]
            dashboard_data[wu.patient.pk] = demographics
        else:
            # adds repeat workups to date list to be used in js side date filtering
            existing_wu_dates = dashboard_data.get(wu.patient.pk)['wu_dates']
            existing_wu_dates.append(str(wu.written_datetime.date()))
    return dashboard_data


def send_all_json(request):
    all_workups = query_all_workups()
    dashboard_data = extract_demographic_data(all_workups)
    return JsonResponse(dashboard_data)

# def send_hypertension_json(request):
#     hypertensive_workups = query_hypertension_workups()
#     dashboard_data = extract_demographic_data(hypertensive_workups)
#     return JsonResponse(dashboard_data)

# def send_diabetes_json(request):
#     diabetes_workups = query_diabetes_workups()
#     dashboard_data = extract_demographic_data(diabetes_workups)
#     return JsonResponse(dashboard_data)

# @active_permission_required('inventory.export_csv', raise_exception=True)
def export_csv(request):
    '''Writes drug models to a new .csv file saved the project root-level folder'''
    data = request.read()
    jsondata = json.loads(data)
    print(jsondata)

    # with NamedTemporaryFile(mode='a+') as file:
    #     writer = csv.writer(file)
    #     header = ['Condition','']
    #     writer.writerow(header)
    #     for drug in drugs:
    #         dispensed_list = list(recently_dispensed.filter(drug=drug.id).values_list('dispense', flat=True))
    #         dispensed_sum = sum(dispensed_list)
    #         if dispensed_sum == 0:
    #             dispensed_sum = ""
    #         writer.writerow(
    #             [drug.name,
    #              drug.dose,
    #              drug.unit,
    #              drug.category,
    #              drug.stock,
    #              drug.lot_number,
    #              drug.expiration_date,
    #              drug.manufacturer,
    #              dispensed_sum
    #              ])
    #     file.seek(0)
    #     csvfileread = file.read()

    csv_filename = f"test.csv"
    response = HttpResponse('application/csv')

    # response["Content-Disposition"] = (
    #     "attachment; filename=%s" % (csv_filename,))
    return response