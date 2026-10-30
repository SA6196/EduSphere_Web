import ast, pathlib, json, re
from decimal import Decimal, InvalidOperation
f=pathlib.Path(__file__).resolve().parents[1] / 'Backend/quiz/auto_grader.py'
tree=ast.parse(f.read_text()); sel=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('_d','_normalize','_score_question')]; m=ast.Module(body=sel, type_ignores=[]);scope={'Decimal':Decimal,'InvalidOperation':InvalidOperation,'json':json,'re':re};exec(compile(m,str(f),'exec'),scope)
s=scope['_score_question'];cases=[
 ('MCQ_SINGLE correct',{'question_type':'MCQ_SINGLE','question_marks':10,'options':[{'option_id':1,'is_correct':'Y'},{'option_id':2,'is_correct':'N'}]}, {},[1],[],[],10),
 ('MCQ_SINGLE incorrect',{'question_type':'MCQ_SINGLE','question_marks':10,'options':[{'option_id':1,'is_correct':'Y'},{'option_id':2,'is_correct':'N'}]}, {},[2],[],[],0),
 ('MCQ_MULTI exact',{'question_type':'MCQ_MULTI','question_marks':10,'options':[{'option_id':1,'is_correct':'Y'},{'option_id':2,'is_correct':'Y'},{'option_id':3,'is_correct':'N'}]}, {},[2,1],[],[],10),
 ('MCQ_MULTI extra',{'question_type':'MCQ_MULTI','question_marks':10,'options':[{'option_id':1,'is_correct':'Y'},{'option_id':2,'is_correct':'Y'},{'option_id':3,'is_correct':'N'}]}, {},[2,1,3],[],[],0),
 ('TRUE_FALSE',{'question_type':'TRUE_FALSE','question_marks':10,'options':[{'option_id':1,'is_correct':'Y'},{'option_id':2,'is_correct':'N'}]}, {},[1],[],[],10),
 ('NUMERICAL tolerance',{'question_type':'NUMERICAL','question_marks':10,'numeric_rule':{'expected_value':100,'tolerance':0.5}}, {'response_text':'100.4'},[],[],[],10),
 ('SHORT_TEXT normalized',{'question_type':'SHORT_TEXT','question_marks':10,'keywords':[{'keyword_text':'  Oracle  Database '}]},{'response_text':'ORACLE database'},[],[],[],10),
 ('FILL_BLANK ordered',{'question_type':'FILL_BLANK','question_marks':10,'keywords':[{'keyword_order':1,'keyword_text':'SQL'},{'keyword_order':2,'keyword_text':'Oracle'}]}, {'response_text':'["sql","oracle"]'},[],[],[],10),
 ('FILL_BLANK mismatch',{'question_type':'FILL_BLANK','question_marks':10,'keywords':[{'keyword_order':1,'keyword_text':'SQL'},{'keyword_order':2,'keyword_text':'Oracle'}]}, {'response_text':'["sql","MySQL"]'},[],[],[],0),
 ('ORDERING partial',{'question_type':'ORDERING','question_marks':9,'options':[{'option_id':1,'option_order':1},{'option_id':2,'option_order':2},{'option_id':3,'option_order':3}]},{},[],[{'position_order':1,'option_id':1},{'position_order':2,'option_id':3},{'position_order':3,'option_id':2}],[],3),
 ('MATCHING correct',{'question_type':'MATCHING','question_marks':10,'matching_pairs':[{'left_option_id':1,'right_option_id':2}]}, {},[],[],[{'left_option_id':1,'right_option_id':2}],10),
 ('LONG_TEXT pending',{'question_type':'LONG_TEXT','question_marks':10}, {},[],[],[],0),
 ('MCQ no answer key',{'question_type':'MCQ_MULTI','question_marks':10,'options':[]}, {},[],[],[],0),
]
fail=[]
for name,q,resp,sel,order,match,expected in cases:
 try:
  got=s(q,resp,sel,order,match)[0]
  if got!=Decimal(expected):fail.append((name,str(got),str(expected)))
  print(('PASS' if got==Decimal(expected) else 'FAIL'),name,got)
 except Exception as e:fail.append((name,type(e).__name__,str(e)));print('ERROR',name,repr(e))
print('TOTAL',len(cases),'PASSED',len(cases)-len(fail),'FAILED',len(fail));exit(bool(fail))
