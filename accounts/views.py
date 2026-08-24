from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout

from .forms import TeacherRegistrationForm, StudentRegistrationForm, LoginForm


def teacher_register(request):

    if request.method == 'POST':
        form = TeacherRegistrationForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('teacher_registration_success')

    else:
        form = TeacherRegistrationForm()

    return render(
        request,
        'accounts/teacher_register.html',
        {'form': form}
    )


def teacher_registration_success(request):
    return render(
        request,
        'accounts/teacher_registration_success.html'
    )


def teacher_login(request):

    if request.method == 'POST':
        form = LoginForm(request.POST)

        if form.is_valid():

            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            user = authenticate(
                request,
                username=username,
                password=password
            )

            if user is not None:

                if user.role != 'teacher':
                    form.add_error(
                        None,
                        'This login is only for teachers.'
                    )

                else:
                    teacher_profile = user.teacher_profile

                    if teacher_profile.verification_status == 'approved':
                        login(request, user)
                        return redirect('teacher_dashboard')

                    elif teacher_profile.verification_status == 'pending':
                        form.add_error(
                            None,
                            'Your account is waiting for administrator approval.'
                        )

                    else:
                        form.add_error(
                            None,
                            'Your teacher account has been rejected.'
                        )

            else:
                form.add_error(
                    None,
                    'Invalid username or password.'
                )

    else:
        form = LoginForm()

    return render(
        request,
        'accounts/teacher_login.html',
        {'form': form}
    )


def user_logout(request):
    logout(request)
    return redirect('teacher_login')

def teacher_dashboard(request):
    return render(
        request,
        'accounts/teacher_dashboard.html'
    )

def teacher_dashboard(request):
    return render(request, 'accounts/teacher_dashboard.html')

def home(request):
    return render(request, 'home.html')

def student_register(request):

    if request.method == 'POST':
        form = StudentRegistrationForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('student_registration_success')

    else:
        form = StudentRegistrationForm()

    return render(
        request,
        'accounts/student_register.html',
        {'form': form}
    )
def student_registration_success(request):
    return render(
        request,
        'accounts/student_registration_success.html'
    )