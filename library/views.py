from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Author, Book, Member, Loan
from .serializers import AuthorSerializer, BookSerializer, MemberSerializer, LoanSerializer
from rest_framework.decorators import action
from django.utils import timezone
from .tasks import send_loan_notification
from .serializers_extra import ExtendDueDateSerializer
from datetime import timedelta
from django.db.models import Count, Q
from .serializers_extra import ActiveMemberSerializer

class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

class BookViewSet(viewsets.ModelViewSet):
    queryset = (
        Book.objects
        .select_related("author")
        .prefetch_related("genres")
    )
    serializer_class = BookSerializer

    @action(detail=True, methods=['post'])
    def loan(self, request, pk=None):
        book = self.get_object()
        if book.available_copies < 1:
            return Response({'error': 'No available copies.'}, status=status.HTTP_400_BAD_REQUEST)
        member_id = request.data.get('member_id')
        try:
            member = Member.objects.get(id=member_id)
        except Member.DoesNotExist:
            return Response({'error': 'Member does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        loan = Loan.objects.create(book=book, member=member)
        book.available_copies -= 1
        book.save()
        send_loan_notification.delay(loan.id)
        return Response({'status': 'Book loaned successfully.'}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def return_book(self, request, pk=None):
        book = self.get_object()
        member_id = request.data.get('member_id')
        try:
            loan = Loan.objects.get(book=book, member__id=member_id, is_returned=False)
        except Loan.DoesNotExist:
            return Response({'error': 'Active loan does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        loan.is_returned = True
        loan.return_date = timezone.now().date()
        loan.save()
        book.available_copies += 1
        book.save()
        return Response({'status': 'Book returned successfully.'}, status=status.HTTP_200_OK)

class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer
    
    @action(detail=False, method=["get"], url_path="top-active")
    def top_active(self, request):
        qs = (
            Member.objects.selected_related("user")
            .annotate(active_loans=Count("loans", filter=Q(loans_is_returned=False)))
            .filter(active_loans__gt=0)
            .prder_by("-active_loans", "id")[:5]
        )
        
        return Response(ActiveMemberSerializer(qs, many=True).data)

class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all()
    serializer_class = LoanSerializer
    
    @action(detail=True, methods=["post"], url_path="extend_due_date")
    def extend_due_date(self, request, pk=None):
        loan = self.get_object()
        
        if loan.due_date and loan.due_date < timezone.now().date():
            return Response({"detail": "Loan is already overdue."}, status=status.HTTP_400_BAD_REQUEST)
        
        ser = ExtendDueDateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        loan.due_date(loan.due_date or loan.loan_date) + timedelta(days=ser.validated_data["additional_days"])
        loan.save(update_fields=["due_date"])
        return Response(LoanSerializer(loan).data, status=status.HTTP_200_OK)
