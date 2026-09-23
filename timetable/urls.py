from django.urls import path
from .views import (
    TimetableListView,
    TimetableDetailView,
    TimetableCreateView,
    TimetableUpdateView,
    TimetableDeleteView,
    MyTimetableView,
    ClassroomTimetableView,
)

urlpatterns = [
    path("", TimetableListView.as_view(), name="timetable-list"),
    path("<int:pk>/", TimetableDetailView.as_view(), name="timetable-detail"),     
    path("create/", TimetableCreateView.as_view(), name="timetable-create"),
    path("update/<int:pk>/", TimetableUpdateView.as_view(), name="timetable-update"),
    path("delete/<int:pk>/", TimetableDeleteView.as_view(), name="timetable-delete"),    
    path("my-timetable/", MyTimetableView.as_view(),name="my-timetable",),
    path( "classroom/<int:classroom_id>/", ClassroomTimetableView.as_view(), name="classroom-timetable",),
]
