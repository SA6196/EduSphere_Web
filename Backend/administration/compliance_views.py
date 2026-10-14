from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import IsAdmin
from .compliance import save_master_data, audit_overview

class MasterDataCollectionView(APIView):
    permission_classes=[IsAuthenticated, IsAdmin]
    def post(self, request, kind):
        return Response({"success": True, "data": save_master_data(request.user.user_id, request.user.role, kind, request.data)})

class MasterDataDetailView(APIView):
    permission_classes=[IsAuthenticated, IsAdmin]
    def put(self, request, kind, record_id):
        return Response({"success": True, "data": save_master_data(request.user.user_id, request.user.role, kind, request.data, record_id)})

class AdminAuditView(APIView):
    permission_classes=[IsAuthenticated, IsAdmin]
    def get(self, request):
        return Response({"success":True,"data":audit_overview(request.user.role, request.query_params.get('q',''), request.query_params.get('limit',100))})


class StudentApprovalView(APIView):
    permission_classes=[IsAuthenticated,IsAdmin]
    def post(self,request,student_id):
        from accounts.registration import activate_student
        return Response({'success':True,'data':activate_student(student_id,request.user.user_id)})
