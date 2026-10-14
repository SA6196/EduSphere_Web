# EduSphere API Quickstart
# Replace placeholder passwords; never commit real passwords or tokens.

$BaseUrl = "http://127.0.0.1:8000"

function Login-EduSphere {
    param(
        [Parameter(Mandatory=$true)][string]$Username,
        [Parameter(Mandatory=$true)][string]$Password
    )
    $body = @{ username=$Username; password=$Password } | ConvertTo-Json
    Invoke-RestMethod -Uri "$BaseUrl/api/auth/login/" -Method POST -ContentType "application/json" -Body $body
}

function Refresh-EduSphereAccessToken {
    param([Parameter(Mandatory=$true)][string]$RefreshToken)
    $body = @{ refresh=$RefreshToken } | ConvertTo-Json
    (Invoke-RestMethod -Uri "$BaseUrl/api/auth/refresh/" -Method POST -ContentType "application/json" -Body $body).access
}

function Get-EduSphereHeaders {
    param([Parameter(Mandatory=$true)][string]$AccessToken)
    @{ Authorization = "Bearer $AccessToken" }
}

# Examples:
# $student = Login-EduSphere "FINAL_S7" "<student-password>"
# $studentToken = $student.access
# $studentRefresh = $student.refresh
# $studentHeaders = Get-EduSphereHeaders $studentToken
# Invoke-RestMethod -Uri "$BaseUrl/api/auth/me/" -Headers $studentHeaders
# Invoke-RestMethod -Uri "$BaseUrl/api/gpa/my/" -Headers $studentHeaders | ConvertTo-Json -Depth 12
# $studentToken = Refresh-EduSphereAccessToken $studentRefresh

# $instructor = Login-EduSphere "FINAL_I1" "<instructor-password>"
# $instructorHeaders = Get-EduSphereHeaders $instructor.access
# Invoke-RestMethod -Uri "$BaseUrl/api/instructor/offerings/" -Headers $instructorHeaders

# $admin = Login-EduSphere "FINAL_ADMIN" "<admin-password>"
# $adminHeaders = Get-EduSphereHeaders $admin.access
# Invoke-RestMethod -Uri "$BaseUrl/api/reports/admin/overview/" -Headers $adminHeaders | ConvertTo-Json -Depth 12

# POST helper pattern:
# $body = @{ offering_id = 3 } | ConvertTo-Json
# Invoke-RestMethod -Uri "$BaseUrl/api/enrollments/" -Method POST -Headers $studentHeaders -ContentType "application/json" -Body $body
