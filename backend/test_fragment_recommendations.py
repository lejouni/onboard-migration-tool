"""Test complete workflow enhancement flow with step fragments"""
from database import SessionLocal
from workflow_enhancement_helpers import generate_enhancement_recommendations
from assessment_logic import AssessmentRecommendation, AssessmentType, PackageManagerDetection

# Mock workflow analysis for a repo with a build job
mock_workflow_analysis = {
    'file': {
        'name': 'ci.yml',
        'path': '.github/workflows/ci.yml'
    },
    'analysis': {
        'has_build_job': True,
        'has_pr_trigger': True,
        'jobs': {
            'build': {
                'has_build_steps': True,
                'build_tools': ['npm'],
                'languages': ['javascript']
            },
            'test': {
                'has_build_steps': False
            }
        },
        'insertion_points': [
            {
                'location': 'after_build',
                'after_job': 'build',
                'reasoning': 'Add security scan after build job'
            }
        ]
    }
}

# Mock assessment recommendation
mock_assessment = AssessmentRecommendation(
    assessment_type=AssessmentType.SAST_SCA,
    primary_language='javascript',
    reasoning='Detected JavaScript project with package.json, recommend SAST and SCA',
    package_managers=[
        PackageManagerDetection(
            detected=True,
            package_manager='npm',
            files_found=['package.json', 'package-lock.json'],
            languages=['javascript']
        )
    ]
)

def test_step_fragment_recommendation():
    """Test that step fragments are recommended when appropriate"""
    db = SessionLocal()
    
    try:
        print("\n=== TEST: Step Fragment Recommendation ===\n")
        
        # Generate recommendations
        recommendations = generate_enhancement_recommendations(
            db=db,
            repo_name='test/repo',
            parsed_workflows=[mock_workflow_analysis],
            assessment_recommendation=mock_assessment,
            detected_languages=['javascript']
        )
        
        print(f"Generated {len(recommendations)} recommendation(s)\n")
        
        for i, rec in enumerate(recommendations, 1):
            print(f"Recommendation {i}:")
            print(f"  Template: {rec['template_name']}")
            print(f"  Type: {rec['type']}")
            print(f"  Fragment Type: {rec['template_fragment_type']}")
            print(f"  Category: {rec['category']}")
            print(f"  Assessment: {rec['assessment_type']}")
            
            if rec['template_fragment_type'] == 'step':
                print(f"  ✅ STEP FRAGMENT - Will insert into existing job")
                print(f"  Target Job: {rec['target_workflow']['insertion_point']['target_job']}")
                print(f"  Location: {rec['target_workflow']['insertion_point']['location']}")
                print(f"  Reasoning: {rec['target_workflow']['insertion_point']['reasoning']}")
            else:
                print(f"  JOB FRAGMENT - Will add new job")
                print(f"  Insertion: {rec['target_workflow']['insertion_point']['location']}")
            
            print(f"  Reason: {rec['reason']}")
            print()
        
        # Check if we got step fragments
        step_fragments = [r for r in recommendations if r['template_fragment_type'] == 'step']
        job_fragments = [r for r in recommendations if r['template_fragment_type'] == 'job']
        
        print(f"Step fragments: {len(step_fragments)}")
        print(f"Job fragments: {len(job_fragments)}")
        
        if step_fragments:
            print("\n✅ SUCCESS: Step fragments are being recommended for repos with build jobs!")
        else:
            print("\n⚠️  WARNING: No step fragments recommended (might use job fragments instead)")
        
    finally:
        db.close()

def test_job_fragment_recommendation():
    """Test that job fragments are recommended when no suitable build job exists"""
    db = SessionLocal()
    
    try:
        print("\n=== TEST: Job Fragment Recommendation (No Build Job) ===\n")
        
        # Mock workflow WITHOUT build job
        workflow_no_build = {
            'file': {
                'name': 'test.yml',
                'path': '.github/workflows/test.yml'
            },
            'analysis': {
                'has_build_job': False,
                'has_pr_trigger': True,
                'jobs': {
                    'test': {
                        'has_build_steps': False
                    }
                },
                'insertion_points': [
                    {
                        'location': 'end',
                        'after_job': None,
                        'reasoning': 'Add at end of workflow'
                    }
                ]
            }
        }
        
        recommendations = generate_enhancement_recommendations(
            db=db,
            repo_name='test/repo',
            parsed_workflows=[workflow_no_build],
            assessment_recommendation=mock_assessment,
            detected_languages=['javascript']
        )
        
        print(f"Generated {len(recommendations)} recommendation(s)\n")
        
        for rec in recommendations:
            print(f"Template: {rec['template_name']}")
            print(f"Fragment Type: {rec['template_fragment_type']}")
            
        job_fragments = [r for r in recommendations if r['template_fragment_type'] == 'job']
        
        if job_fragments:
            print("\n✅ SUCCESS: Job fragments recommended when no build job exists!")
        else:
            print("\n❌ FAIL: Should recommend job fragments when no build job")
        
    finally:
        db.close()

if __name__ == '__main__':
    test_step_fragment_recommendation()
    test_job_fragment_recommendation()
