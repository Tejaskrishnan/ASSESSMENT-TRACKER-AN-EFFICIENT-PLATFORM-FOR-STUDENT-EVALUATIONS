import json
import math
from datetime import datetime

from django.contrib import messages
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse, JsonResponse
from django.shortcuts import (HttpResponseRedirect, get_object_or_404,
                              redirect, render)
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.db.models import Sum

from .forms import *
from .models import *


def student_home(request):
    student = get_object_or_404(Student, admin=request.user)
    total_subject = Subject.objects.filter(course=student.course).count()
    total_attendance = AttendanceReport.objects.filter(student=student).count()
    total_present = AttendanceReport.objects.filter(student=student, status=True).count()
    if total_attendance == 0:  # Avoid DivisionByZero
        percent_absent = percent_present = 0
    else:
        percent_present = math.floor((total_present / total_attendance) * 100)
        percent_absent = math.ceil(100 - percent_present)
    subject_name = []
    data_present = []
    data_absent = []
    subjects = Subject.objects.filter(course=student.course)
    for subject in subjects:
        attendance = Attendance.objects.filter(subject=subject)
        present_count = AttendanceReport.objects.filter(
            attendance__in=attendance, status=True, student=student).count()
        absent_count = AttendanceReport.objects.filter(
            attendance__in=attendance, status=False, student=student).count()
        subject_name.append(subject.name)
        data_present.append(present_count)
        data_absent.append(absent_count)
    context = {
        'total_attendance': total_attendance,
        'percent_present': percent_present,
        'percent_absent': percent_absent,
        'total_subject': total_subject,
        'subjects': subjects,
        'data_present': data_present,
        'data_absent': data_absent,
        'data_name': subject_name,
        'page_title': 'Student Homepage'
    }
    return render(request, 'student_template/home_content.html', context)


@csrf_exempt
def student_view_attendance(request):
    student = get_object_or_404(Student, admin=request.user)
    if request.method != 'POST':
        course = get_object_or_404(Course, id=student.course.id)
        context = {
            'subjects': Subject.objects.filter(course=course),
            'page_title': 'View Attendance'
        }
        return render(request, 'student_template/student_view_attendance.html', context)
    else:
        subject_id = request.POST.get('subject')
        start = request.POST.get('start_date')
        end = request.POST.get('end_date')
        try:
            subject = get_object_or_404(Subject, id=subject_id)
            start_date = datetime.strptime(start, "%Y-%m-%d")
            end_date = datetime.strptime(end, "%Y-%m-%d")
            attendance = Attendance.objects.filter(
                date__range=(start_date, end_date), subject=subject)
            attendance_reports = AttendanceReport.objects.filter(
                attendance__in=attendance, student=student)
            json_data = []
            for report in attendance_reports:
                data = {
                    "date": str(report.attendance.date),
                    "status": report.status
                }
                json_data.append(data)
            return JsonResponse(json.dumps(json_data), safe=False)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)


def student_apply_leave(request):
    form = LeaveReportStudentForm(request.POST or None)
    student = get_object_or_404(Student, admin_id=request.user.id)
    context = {
        'form': form,
        'leave_history': LeaveReportStudent.objects.filter(student=student),
        'page_title': 'Apply for Leave'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.student = student
                obj.save()
                messages.success(
                    request, "Application for leave has been submitted for review")
                return redirect(reverse('student_apply_leave'))
            except Exception:
                messages.error(request, "Could not submit")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "student_template/student_apply_leave.html", context)


def student_feedback(request):
    form = FeedbackStudentForm(request.POST or None)
    student = get_object_or_404(Student, admin_id=request.user.id)
    context = {
        'form': form,
        'feedbacks': FeedbackStudent.objects.filter(student=student),
        'page_title': 'Student Feedback'
    }
    if request.method == 'POST':
        if form.is_valid():
            try:
                obj = form.save(commit=False)
                obj.student = student
                obj.save()
                messages.success(
                    request, "Feedback submitted for review")
                return redirect(reverse('student_feedback'))
            except Exception:
                messages.error(request, "Could not Submit!")
        else:
            messages.error(request, "Form has errors!")
    return render(request, "student_template/student_feedback.html", context)


def student_view_profile(request):
    student = get_object_or_404(Student, admin=request.user)
    form = StudentEditForm(request.POST or None, request.FILES or None,
                           instance=student)
    context = {
        'form': form,
        'page_title': 'View/Edit Profile'
    }
    if request.method == 'POST':
        try:
            if form.is_valid():
                first_name = form.cleaned_data.get('first_name')
                last_name = form.cleaned_data.get('last_name')
                password = form.cleaned_data.get('password') or None
                address = form.cleaned_data.get('address')
                gender = form.cleaned_data.get('gender')
                passport = request.FILES.get('profile_pic') or None
                admin = student.admin
                if password:
                    admin.set_password(password)
                if passport:
                    fs = FileSystemStorage()
                    filename = fs.save(passport.name, passport)
                    passport_url = fs.url(filename)
                    admin.profile_pic = passport_url
                admin.first_name = first_name
                admin.last_name = last_name
                admin.address = address
                admin.gender = gender
                admin.save()
                student.save()
                messages.success(request, "Profile Updated!")
                return redirect(reverse('student_view_profile'))
            else:
                messages.error(request, "Invalid Data Provided")
        except Exception as e:
            messages.error(request, f"Error Occurred While Updating Profile: {str(e)}")
    return render(request, "student_template/student_view_profile.html", context)


@csrf_exempt
def student_fcmtoken(request):
    token = request.POST.get('token')
    student_user = get_object_or_404(CustomUser, id=request.user.id)
    try:
        student_user.fcm_token = token
        student_user.save()
        return HttpResponse("True")
    except Exception:
        return HttpResponse("False")


def student_view_notification(request):
    student = get_object_or_404(Student, admin=request.user)
    notifications = NotificationStudent.objects.filter(student=student)
    context = {
        'notifications': notifications,
        'page_title': "View Notifications"
    }
    return render(request, "student_template/student_view_notification.html", context)


def student_view_result(request):
    student = get_object_or_404(Student, admin=request.user)
    results = StudentResult.objects.filter(student=student)
    context = {
        'results': results,
        'page_title': "View Results"
    }
    return render(request, "student_template/student_view_result.html", context)


@login_required
@csrf_exempt
def student_compare_subjects(request):
    student = get_object_or_404(Student, admin=request.user)
    if request.method == 'POST':
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        try:
            if not start_date or not end_date:
                raise ValueError("Start date and end date are required.")
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            if start > end:
                raise ValueError("Start date must be before end date.")
            print(f"Fetching results for {student.admin.email} from {start} to {end}")
            results = StudentResult.objects.filter(
                student=student,
                created_at__range=(start, end)
            ).values('subject__name').annotate(
                total_test=Sum('test'),
                total_exam=Sum('exam')
            )
            subjects = [result['subject__name'] for result in results]
            test_scores = [float(result['total_test'] or 0) for result in results]
            exam_scores = [float(result['total_exam'] or 0) for result in results]
            print(f"Results: {subjects}, Test: {test_scores}, Exam: {exam_scores}")
            return JsonResponse({
                'subjects': subjects,
                'test_scores': test_scores,
                'exam_scores': exam_scores
            })
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            print(f"Error in student_compare_subjects: {str(e)}")
            return JsonResponse({'error': f"Server error: {str(e)}"}, status=500)
    context = {'page_title': 'Compare Subjects'}
    return render(request, 'student_template/student_compare_subjects.html', context)

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from main_app.models import Student, StudentResult, Staff
from datetime import datetime
from django.db.models import Sum  # Required for aggregation

@login_required
@csrf_exempt
def student_compare_teachers(request):
    student = get_object_or_404(Student, admin=request.user)
    if request.method == 'POST':
        teacher_id = request.POST.get('teacher')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        print(f"Request received: {request.method}, User: {student.admin.email}")
        print(f"POST data: teacher={teacher_id}, start={start_date}, end={end_date}")
        try:
            if not teacher_id or not start_date or not end_date:
                raise ValueError("Teacher, start date, and end date are required.")
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            if start > end:
                raise ValueError("Start date must be before end date.")
            print(f"Fetching results for {student.admin.email}, Teacher ID: {teacher_id}, {start} to {end}")
            results = StudentResult.objects.filter(
                student=student,
                subject__staff__id=teacher_id,
                created_at__range=(start, end)
            ).values('subject__name').annotate(
                total_score=Sum('test') + Sum('exam')
            )
            print(f"Number of results: {results.count()}")
            for result in results:
                print(f"Raw result: {result}")
            subjects = [result['subject__name'] for result in results]
            scores = [float(result['total_score'] or 0) for result in results]
            print(f"Processed: Subjects: {subjects}, Scores: {scores}")
            return JsonResponse({
                'subjects': subjects,
                'scores': scores
            })
        except ValueError as e:
            print(f"ValueError: {e}")
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            print(f"Error in student_compare_teachers: {str(e)}")
            return JsonResponse({'error': f"Server error: {str(e)}"}, status=500)
    staff_list = Staff.objects.all()
    context = {'staff_list': staff_list, 'page_title': 'Compare with Teachers'}
    return render(request, 'student_template/student_compare_teachers.html', context)

@login_required
@csrf_exempt
def student_compare_all_teachers(request):
    student = get_object_or_404(Student, admin=request.user)
    if request.method == 'POST':
        start_date = request.POST.get('start_date', None)
        end_date = request.POST.get('end_date', None)
        try:
            filters = {'student': student}
            if start_date and end_date:
                start = datetime.strptime(start_date, "%Y-%m-%d")
                end = datetime.strptime(end_date, "%Y-%m-%d")
                if start > end:
                    raise ValueError("Start date must be before end date.")
                filters['created_at__range'] = (start, end)
                print(f"Filtering {student.admin.email} from {start} to {end}")
            else:
                print(f"Fetching all results for {student.admin.email}")
            results = StudentResult.objects.filter(**filters).values(
                'subject__staff__admin__first_name', 'subject__staff__admin__last_name'
            ).annotate(
                total_score=Sum('test') + Sum('exam')
            )
            teachers = [f"{result['subject__staff__admin__first_name']} {result['subject__staff__admin__last_name']}" for result in results]
            scores = [float(result['total_score'] or 0) for result in results]
            print(f"Results: {teachers}, Scores: {scores}")
            return JsonResponse({
                'teachers': teachers,
                'scores': scores
            })
        except ValueError as e:
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            print(f"Error in student_compare_all_teachers: {str(e)}")
            return JsonResponse({'error': f"Server error: {str(e)}"}, status=500)
    context = {'page_title': 'Compare with All Teachers'}
    return render(request, 'student_template/student_compare_all_teachers.html', context)

@login_required
@csrf_exempt
def student_compare_one_subject(request):
    student = get_object_or_404(Student, admin=request.user)
    if request.method == 'POST':
        subject_id = request.POST.get('subject')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        print(f"Request received: {request.method}, User: {student.admin.email}")
        print(f"POST data: subject={subject_id}, start={start_date}, end={end_date}")
        try:
            if not subject_id or not start_date or not end_date:
                raise ValueError("Subject, start date, and end date are required.")
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            if start > end:
                raise ValueError("Start date must be before end date.")
            print(f"Fetching results for {student.admin.email}, Subject ID: {subject_id}, {start} to {end}")
            results = StudentResult.objects.filter(
                student=student,
                subject__id=subject_id,
                created_at__range=(start, end)
            ).values('subject__name').annotate(
                total_score=Sum('test') + Sum('exam')
            )
            print(f"Number of results: {results.count()}")
            for result in results:
                print(f"Raw result: {result}")
            if results.exists():
                subject_name = results[0]['subject__name']
                total_score = float(results[0]['total_score'] or 0)
            else:
                subject_name = Subject.objects.get(id=subject_id).name
                total_score = 0
            print(f"Processed: Subject: {subject_name}, Total Score: {total_score}")
            return JsonResponse({
                'subject': subject_name,
                'score': total_score
            })
        except ValueError as e:
            print(f"ValueError: {e}")
            return JsonResponse({'error': str(e)}, status=400)
        except Exception as e:
            print(f"Error in student_compare_one_subject: {str(e)}")
            return JsonResponse({'error': f"Server error: {str(e)}"}, status=500)
    subjects = Subject.objects.filter(course=student.course)  # Only subjects in student's course
    context = {'subjects': subjects, 'page_title': 'Compare One Subject'}
    return render(request, 'student_template/student_compare_one_subject.html', context)


def student_view_holistic_evaluation(request):
    student = get_object_or_404(Student, admin=request.user)
    evaluations = HolisticEvaluation.objects.filter(student=student)
    context = {
        'evaluations': evaluations,
        'page_title': 'View Holistic Evaluation'
    }
    return render(request, 'student_template/student_view_holistic_evaluation.html', context)

def student_compare_holistic_evaluation(request):
    student = get_object_or_404(Student, admin=request.user)
    evaluations = HolisticEvaluation.objects.filter(student=student)
    if not evaluations.exists():
        context = {
            'page_title': 'Compare Holistic Evaluation',
            'no_data': True
        }
    else:
        sessions = Session.objects.filter(id__in=evaluations.values_list('session', flat=True))
        session_labels = [str(session) for session in sessions]
        data = {
            'problem_solving': [e.problem_solving_skills for e in evaluations],
            'integrity': [e.integrity for e in evaluations],
            'leadership': [e.leadership for e in evaluations],
            'discipline': [e.discipline for e in evaluations],
            'collaboration': [e.collaboration for e in evaluations],
            'extra_curricular': [e.extra_curricular_activities for e in evaluations],
            'total_score': [e.total_score() for e in evaluations]
        }
        context = {
            'sessions': json.dumps(session_labels),  # JSON-encode for JavaScript
            'data': json.dumps(data),  # JSON-encode for JavaScript
            'page_title': 'Compare Holistic Evaluation',
            'no_data': False
        }
    return render(request, 'student_template/student_compare_holistic_evaluation.html', context)