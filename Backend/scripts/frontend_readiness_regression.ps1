param(
    [Parameter(Mandatory=$true)][string]$StudentToken,
    [Parameter(Mandatory=$true)][string]$Instructor1Token,
    [Parameter(Mandatory=$true)][string]$Instructor2Token,
    [Parameter(Mandatory=$true)][string]$AdminToken,
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [int]$OfferingId = 3,
    [int]$QuizId = 41,
    [int]$QuizComponentId = 41,
    [int]$QuestionId = 41,
    [int]$SubmittedAttemptId = 43,
    [int]$EnrollmentId = 36
)

$pass = 0
$fail = 0

function Invoke-Status {
    param(
        [string]$Method,
        [string]$Url,
        [string]$Token,
        $Body = $null
    )

    $headers = @{}
    if ($Token) { $headers.Authorization = "Bearer $Token" }
    $params = @{
        Uri = $Url
        Method = $Method
        Headers = $headers
        UseBasicParsing = $true
        ErrorAction = "Stop"
    }
    if ($null -ne $Body) {
        $params.ContentType = "application/json"
        $params.Body = ($Body | ConvertTo-Json -Depth 10)
    }

    try {
        $r = Invoke-WebRequest @params
        return @{ Status = [int]$r.StatusCode; Content = $r.Content }
    }
    catch {
        $status = 0
        if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
            $status = [int]$_.Exception.Response.StatusCode
        }
        $content = $_.ErrorDetails.Message
        return @{ Status = $status; Content = $content }
    }
}

function Check {
    param([string]$Name, [int[]]$Expected, $Result)
    if ($Expected -contains $Result.Status) {
        Write-Host "[PASS] $Name -> HTTP $($Result.Status)"
        $script:pass++
    }
    else {
        Write-Host "[FAIL] $Name -> expected $($Expected -join '/'), got $($Result.Status)"
        if ($Result.Content) { Write-Host "       $($Result.Content)" }
        $script:fail++
    }
}

Write-Host "=== EduSphere frontend-readiness regression ==="

Check "Offering grading - assigned instructor" @(200) (Invoke-Status GET "$BaseUrl/api/offerings/$OfferingId/grading/" $Instructor2Token)
Check "Offering grading - enrolled student" @(200) (Invoke-Status GET "$BaseUrl/api/offerings/$OfferingId/grading/" $StudentToken)
Check "Instructor roster - assigned instructor" @(200) (Invoke-Status GET "$BaseUrl/api/instructor/offerings/$OfferingId/roster/" $Instructor2Token)
Check "Instructor roster - unassigned instructor" @(403) (Invoke-Status GET "$BaseUrl/api/instructor/offerings/$OfferingId/roster/" $Instructor1Token)
Check "Instructor roster - admin" @(200) (Invoke-Status GET "$BaseUrl/api/instructor/offerings/$OfferingId/roster/" $AdminToken)
Check "Question bank list" @(200) (Invoke-Status GET "$BaseUrl/api/quizzes/questions/" $Instructor2Token)
Check "Question detail" @(200) (Invoke-Status GET "$BaseUrl/api/quizzes/questions/$QuestionId/" $Instructor2Token)
Check "Quiz content - assigned instructor" @(200) (Invoke-Status GET "$BaseUrl/api/quizzes/$QuizId/content/" $Instructor2Token)

# Student content is 200 only while an open owned attempt exists; otherwise the
# intended pre-attempt/timer protection is a 400 business-rule response.
Check "Quiz content - student attempt gate" @(200,400) (Invoke-Status GET "$BaseUrl/api/quizzes/$QuizId/content/" $StudentToken)

# The result/review status is determined by the current V6 visibility flags.
$quizList = Invoke-Status GET "$BaseUrl/api/quizzes/?component_id=$QuizComponentId" $Instructor2Token
Check "Quiz list for visibility state" @(200) $quizList
if ($quizList.Status -eq 200) {
    try {
        $json = $quizList.Content | ConvertFrom-Json
        $q = $json.data | Where-Object { $_.quiz_id -eq $QuizId } | Select-Object -First 1
        if ($null -ne $q) {
            $expectedResult = if ($q.allow_mark_view -eq 'Y') { @(200) } else { @(403) }
            $expectedReview = if ($q.allow_answer_review -eq 'Y') { @(200) } else { @(403) }
            Check "Quiz submitted-attempt result visibility" $expectedResult (Invoke-Status GET "$BaseUrl/api/quizzes/attempt/$SubmittedAttemptId/result/" $StudentToken)
            Check "Quiz submitted-attempt review visibility" $expectedReview (Invoke-Status GET "$BaseUrl/api/quizzes/attempt/$SubmittedAttemptId/review/" $StudentToken)
        }
        else {
            Write-Host "[FAIL] Quiz $QuizId not found in component $QuizComponentId list"
            $fail++
        }
    }
    catch {
        Write-Host "[FAIL] Could not parse quiz visibility state"
        $fail++
    }
}

# Rejection tests: these must not write data.
$sessionBody = @{
    offering_id = $OfferingId
    session_date = "2026-10-12"
    start_time = "10:00"
    end_time = "11:00"
    session_type = "LECTURE"
    topic = "FRONTEND_READINESS_REJECTION_TEST"
}
Check "Student blocked from class-session creation" @(403) (Invoke-Status POST "$BaseUrl/api/attendance/sessions/" $StudentToken $sessionBody)
Check "Unassigned instructor blocked from class-session creation" @(403) (Invoke-Status POST "$BaseUrl/api/attendance/sessions/" $Instructor1Token $sessionBody)

$markBody = @{
    component_id = $QuizComponentId
    enrollment_id = $EnrollmentId
    marks_obtained = 1
}
Check "Unassigned instructor blocked from mark recording" @(403) (Invoke-Status POST "$BaseUrl/api/marks/record/" $Instructor1Token $markBody)
Check "Unassigned instructor blocked from grade publication" @(403) (Invoke-Status POST "$BaseUrl/api/grades/publish/" $Instructor1Token @{ enrollment_id = $EnrollmentId })

Write-Host "=== Result: PASS=$pass FAIL=$fail ==="
if ($fail -gt 0) { exit 1 }
