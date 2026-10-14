param(
    [Parameter(Mandatory=$true)][string]$StudentToken,
    [Parameter(Mandatory=$true)][string]$Instructor1Token,
    [Parameter(Mandatory=$true)][string]$Instructor2Token,
    [Parameter(Mandatory=$true)][string]$AdminToken,
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
$script:Passed = 0
$script:Failed = 0

function Invoke-Expect {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Uri,
        [int]$ExpectedStatus,
        [string]$Token = "",
        $Body = $null
    )

    $headers = @{}
    if ($Token) { $headers.Authorization = "Bearer $Token" }

    try {
        $params = @{
            Uri = $Uri
            Method = $Method
            Headers = $headers
            ErrorAction = "Stop"
        }
        if ($null -ne $Body) {
            $params.ContentType = "application/json"
            $params.Body = ($Body | ConvertTo-Json -Depth 8)
        }

        $response = Invoke-WebRequest @params
        $actual = [int]$response.StatusCode
        $payload = $response.Content
    }
    catch {
        if ($null -ne $_.Exception.Response) {
            $actual = [int]$_.Exception.Response.StatusCode.value__
            $payload = $_.ErrorDetails.Message
        }
        else {
            Write-Host "[FAIL] $Name - request error: $($_.Exception.Message)"
            $script:Failed++
            return
        }
    }

    if ($actual -eq $ExpectedStatus) {
        Write-Host "[PASS] $Name -> HTTP $actual"
        $script:Passed++
    }
    else {
        Write-Host "[FAIL] $Name -> expected $ExpectedStatus, got $actual"
        if ($payload) { Write-Host "       $payload" }
        $script:Failed++
    }
}

Write-Host "=== EduSphere final regression ==="

# Authentication semantics
Invoke-Expect "Missing access token is 401" "GET" "$BaseUrl/api/gpa/my/" 401
Invoke-Expect "Invalid access token is 401" "GET" "$BaseUrl/api/gpa/my/" 401 "definitely.invalid.token"

# Positive smoke tests
Invoke-Expect "Student GPA summary" "GET" "$BaseUrl/api/gpa/my/" 200 $StudentToken
Invoke-Expect "Student upcoming exams" "GET" "$BaseUrl/api/exams/my/upcoming/" 200 $StudentToken
Invoke-Expect "Admin overview" "GET" "$BaseUrl/api/reports/admin/overview/" 200 $AdminToken
Invoke-Expect "Admin student progress" "GET" "$BaseUrl/api/reports/student/7/progress/?semester_id=2" 200 $AdminToken

# Authorization semantics
Invoke-Expect "Student blocked from admin reports" "GET" "$BaseUrl/api/reports/admin/overview/" 403 $StudentToken
Invoke-Expect "Instructor blocked from admin reports" "GET" "$BaseUrl/api/reports/offering/3/roster/" 403 $Instructor2Token
Invoke-Expect "Unassigned instructor blocked from offering 3 exams" "GET" "$BaseUrl/api/exams/?offering_id=3" 403 $Instructor1Token
Invoke-Expect "Student blocked from exam scheduling" "POST" "$BaseUrl/api/exams/schedule/" 403 $StudentToken @{
    component_id = 42
    exam_title = "HARDENING Unauthorized Student Exam"
    exam_type = "FINAL"
    exam_date = "2026-10-21"
    start_time = "10:00"
    end_time = "12:00"
}

# Not-found semantics
Invoke-Expect "Unknown exam is 404" "GET" "$BaseUrl/api/exams/999999/" 404 $AdminToken
Invoke-Expect "Unknown announcement is 404" "GET" "$BaseUrl/api/announcements/999999/" 404 $AdminToken
Invoke-Expect "Unknown material is 404" "GET" "$BaseUrl/api/materials/999999/" 404 $StudentToken
Invoke-Expect "Unknown GPA student is 404" "GET" "$BaseUrl/api/gpa/student/999999/" 404 $AdminToken
Invoke-Expect "Unknown report offering is 404" "GET" "$BaseUrl/api/reports/offering/999999/roster/" 404 $AdminToken

# Duplicate / invalid-input semantics (all are safe expected rejections)
Invoke-Expect "Duplicate exam schedule is 400" "POST" "$BaseUrl/api/exams/schedule/" 400 $Instructor2Token @{
    component_id = 42
    exam_title = "HARDENING Duplicate Exam"
    exam_type = "FINAL"
    exam_date = "2026-10-22"
    start_time = "10:00"
    end_time = "12:00"
}

Invoke-Expect "Invalid announcement priority is 400" "POST" "$BaseUrl/api/announcements/create/" 400 $Instructor2Token @{
    offering_id = 3
    announcement_title = "HARDENING Invalid Priority"
    announcement_message = "This request must be rejected."
    announcement_priority = "CRITICAL"
}

Invoke-Expect "Invalid question type is 400" "POST" "$BaseUrl/api/quizzes/questions/create/" 400 $Instructor2Token @{
    question_text = "HARDENING invalid question type"
    question_type = "NOT_A_REAL_TYPE"
}

Invoke-Expect "Invalid material type is 400" "POST" "$BaseUrl/api/materials/create/" 400 $Instructor2Token @{
    offering_id = 3
    material_title = "HARDENING Invalid Material"
    material_type = "EXECUTABLE"
    material_url = "https://example.invalid/test"
}

Write-Host "=== Result: PASS=$script:Passed FAIL=$script:Failed ==="
if ($script:Failed -gt 0) { exit 1 }
exit 0
