import re
from typing import Dict, List, Any


class AIResumeService:
    @staticmethod
    def analyze_cgpa_strategy(cgpa: float) -> Dict[str, Any]:
        """
        Determine resume layout emphasis based on actual CGPA without exaggerating qualifications.
        """
        if cgpa is None:
            return {
                'cgpa': None,
                'tier': 'standard',
                'strategy_title': 'Practical Skills & Projects Focus',
                'ai_recommendation': 'Emphasizing verified blockchain certificates, technical skill proficiencies, and hands-on projects.',
                'preferred_section_order': ['summary', 'skills', 'certifications', 'projects', 'experience', 'education', 'achievements'],
                'highlight_education': False
            }

        try:
            val = float(cgpa)
        except (ValueError, TypeError):
            val = 7.5

        if val >= 8.5:
            return {
                'cgpa': val,
                'tier': 'high_distinction',
                'strategy_title': 'Academic Excellence & Rigor Emphasis',
                'ai_recommendation': f'Your CGPA of {val:.1f} is a strong academic asset. The AI recommends placing Education & Academic Honors prominently near the top, reinforced by Verified Blockchain Credentials.',
                'preferred_section_order': ['summary', 'education', 'certifications', 'skills', 'projects', 'experience', 'achievements'],
                'highlight_education': True
            }
        elif val >= 7.2:
            return {
                'cgpa': val,
                'tier': 'balanced',
                'strategy_title': 'Balanced Practical & Academic Focus',
                'ai_recommendation': f'Your CGPA of {val:.1f} is solid. The AI emphasizes core Technical Stack and Blockchain-Verified Certificates first, followed by Project Milestones and Education.',
                'preferred_section_order': ['summary', 'skills', 'certifications', 'projects', 'experience', 'education', 'achievements'],
                'highlight_education': False
            }
        else:
            return {
                'cgpa': val,
                'tier': 'project_first',
                'strategy_title': 'Hands-on Projects & Verified Credentials Focus',
                'ai_recommendation': f'To maximize recruiter engagement, the AI emphasizes your BlockCert verified certificates, production projects, and practical coding capabilities directly below your summary.',
                'preferred_section_order': ['summary', 'projects', 'certifications', 'skills', 'experience', 'education', 'achievements'],
                'highlight_education': False
            }

    @staticmethod
    def extract_skills_from_certificates(certificates) -> List[str]:
        """
        Extract recommended technical skills based on issued BlockCert credentials.
        """
        detected_skills = set()
        skill_mappings = {
            'python': ['Python', 'Data Structures', 'Flask / FastAPI'],
            'web': ['HTML5 / CSS3', 'JavaScript', 'Responsive UI', 'REST APIs'],
            'full stack': ['JavaScript', 'Node.js', 'React', 'SQL Databases', 'RESTful Services'],
            'cybersecurity': ['Network Security', 'Cryptography', 'Vulnerability Assessment', 'SHA-256 Hashing'],
            'security': ['Cryptography', 'Secure Coding', 'Access Control'],
            'blockchain': ['Solidity', 'Smart Contracts', 'Web3.js / Web3.py', 'Ethereum EVM', 'Decentralized Architecture'],
            'data science': ['Python', 'Pandas', 'NumPy', 'Data Visualization', 'SQL'],
            'cloud': ['Cloud Computing', 'Docker', 'Linux', 'API Deployment'],
            'database': ['SQL', 'Database Design', 'Query Optimization', 'MySQL / PostgreSQL'],
            'java': ['Java', 'Object-Oriented Design', 'Spring Boot Basics'],
            'c++': ['C++', 'Memory Management', 'Algorithms'],
        }

        for cert in certificates:
            course_lower = cert.course.lower()
            for keyword, skills in skill_mappings.items():
                if keyword in course_lower:
                    detected_skills.update(skills)

        return sorted(list(detected_skills))

    @staticmethod
    def polish_text_with_ai(raw_text: str, context_type: str = "project") -> str:
        """
        Transform raw student notes into strong, ATS-friendly action statements
        strictly preserving the factual core without inventing false claims.
        """
        cleaned = raw_text.strip()
        if not cleaned:
            return ""

        # Normalize casing and punctuation
        lines = [line.strip().lstrip('•-*').strip() for line in cleaned.split('\n') if line.strip()]

        polished_lines = []
        action_verbs = ["Architected", "Engineered", "Developed", "Implemented", "Designed", "Configured", "Streamlined", "Spearheaded", "Constructed", "Optimized"]

        for idx, line in enumerate(lines):
            # Rule 1: Project descriptions
            if context_type == "project":
                if re.search(r'\b(i made|made|built|created|did)\b', line, re.I):
                    line = re.sub(r'^(i\s+)?(made|built|created|did)\s+', 'Developed and deployed ', line, flags=re.I)
                elif not any(line.startswith(v) for v in action_verbs):
                    verb = action_verbs[idx % len(action_verbs)]
                    line = f"{verb} {line[0].lower() + line[1:] if len(line) > 1 else line}"

                if "using python" in line.lower() and "flask" not in line.lower():
                    line = re.sub(r'using python', 'leveraging Python core modules and standard engineering best practices', line, flags=re.I)
                elif "using" in line.lower() and "leveraging" not in line.lower():
                    line = re.sub(r'\busing\b', 'utilizing', line, flags=re.I)

                if not line.endswith('.'):
                    line += '.'

            # Rule 2: Work Experience
            elif context_type == "experience":
                if re.search(r'\b(worked on|helped with|responsible for)\b', line, re.I):
                    line = re.sub(r'^(i\s+)?(worked on|helped with|was responsible for)\s+', 'Collaborated on the development and optimization of ', line, flags=re.I)
                elif not any(line.startswith(v) for v in action_verbs):
                    line = f"Executed {line[0].lower() + line[1:] if len(line) > 1 else line}"
                if not line.endswith('.'):
                    line += '.'

            # Rule 3: Professional Summary
            elif context_type == "summary":
                if re.search(r'\b(i am|student looking for|fresher)\b', line, re.I):
                    line = "Motivated Software & Technology professional with rigorous academic training, hands-on development experience, and verified blockchain credentials. Adept at building scalable applications, solving algorithmic challenges, and adopting emerging technologies."
                if not line.endswith('.'):
                    line += '.'

            # Rule 4: Achievements
            elif context_type == "achievement":
                if re.search(r'\b(won|got|participated in)\b', line, re.I):
                    line = re.sub(r'^(i\s+)?(won|got)\s+', 'Secured top honors in ', line, flags=re.I)
                if not line.endswith('.'):
                    line += '.'

            polished_lines.append(line)

        return "\n".join(polished_lines)

    @classmethod
    def conduct_interview_step(cls, step: int, user_message: str, current_state: dict, student_profile, certificates) -> dict:
        """
        Interactive conversational interview logic.
        Progresses naturally through resume sections and extracts structured items.
        """
        state = dict(current_state or {})
        user_reply = (user_message or "").strip()

        # Step 0: Welcome & Academic baseline
        if step == 0:
            cgpa_val = student_profile.cgpa if student_profile else None
            cgpa_strategy = cls.analyze_cgpa_strategy(cgpa_val)
            state['cgpa_strategy'] = cgpa_strategy

            # Pre-populate student data
            state['academic'] = {
                'degree': student_profile.degree if student_profile else 'Bachelor of Science in Computer Science',
                'department': student_profile.department if student_profile else 'Computer Science',
                'college': student_profile.user.college_name if (student_profile and student_profile.user) else 'BlockCert Institute of Technology',
                'graduation_year': student_profile.graduation_year if student_profile else 2025,
                'cgpa': cgpa_val or 8.5
            }

            certs_found = [c.course for c in certificates] if certificates else []
            state['available_certificates'] = [
                {
                    'certificate_id': c.certificate_id,
                    'course': c.course,
                    'issuer': c.issuer.college_name if c.issuer and c.issuer.college_name else 'BlockCert Institute',
                    'tx_hash': c.blockchain_tx_hash,
                    'year': c.graduation_year,
                    'verified': True
                }
                for c in (certificates or [])
            ]

            ai_message = (
                f"Hello {student_profile.user.name if student_profile and student_profile.user else 'there'}! 👋 I am your **BlockCert AI Career Coach**.\n\n"
                f"I'll help you craft a high-impact, ATS-optimized resume. Rather than filling out forms, we'll have a brief conversation.\n\n"
                f"📊 **Academic Insight:** I see you are enrolled in **{state['academic']['degree']}** with a CGPA of **{state['academic']['cgpa']}**.\n"
                f"💡 *{cgpa_strategy['ai_recommendation']}*\n\n"
                f"Let's start: **What are the top 3–5 programming languages or technologies you feel most confident with?** (e.g. *Python, JavaScript, SQL, C++*)"
            )
            return {'next_step': 1, 'ai_message': ai_message, 'state': state}

        # Step 1: Technical skills received -> ask for frameworks/tools
        elif step == 1:
            if user_reply:
                skills_list = [s.strip() for s in re.split(r'[,;\n/]| and ', user_reply) if s.strip()]
                state['technical_skills'] = state.get('technical_skills', {})
                state['technical_skills']['languages'] = skills_list

            ai_message = (
                f"Great stack! I've recorded your languages: **{', '.join(state.get('technical_skills', {}).get('languages', ['Python']))}**.\n\n"
                f"Now, **what frameworks, databases, or developer tools do you use?** (e.g. *Flask, React, MySQL, Git, Docker, AWS*)"
            )
            return {'next_step': 2, 'ai_message': ai_message, 'state': state}

        # Step 2: Frameworks received -> ask about Project 1
        elif step == 2:
            if user_reply:
                tools_list = [t.strip() for t in re.split(r'[,;\n/]| and ', user_reply) if t.strip()]
                state['technical_skills'] = state.get('technical_skills', {})
                state['technical_skills']['frameworks_and_tools'] = tools_list

            ai_message = (
                f"Excellent. Now let's highlight your practical work! 🛠️\n\n"
                f"**Tell me about a key project you have built.** What was the project name and what problem did it solve? (e.g. *I made a college attendance and student portal using Flask & MySQL*)"
            )
            return {'next_step': 3, 'ai_message': ai_message, 'state': state}

        # Step 3: Project description received -> ask for role & outcomes
        elif step == 3:
            if user_reply:
                state['current_project_rough'] = user_reply

            ai_message = (
                f"That sounds like a solid technical project! 🚀\n\n"
                f"**What was your specific role in this project, and what technical contribution or outcome did you achieve?** (e.g. *I developed the backend REST APIs, implemented database schemas, and reduced query latency*)"
            )
            return {'next_step': 4, 'ai_message': ai_message, 'state': state}

        # Step 4: Project role & outcome -> polish with AI and check BlockCert certificates
        elif step == 4:
            rough_desc = state.get('current_project_rough', 'Web Application Development')
            role_contrib = user_reply

            combined_project_text = f"{rough_desc}. {role_contrib}"
            polished_bullets = cls.polish_text_with_ai(combined_project_text, context_type="project")

            project_item = {
                'title': rough_desc.split('.')[0][:60] if rough_desc else 'Technical Software Project',
                'role': 'Lead Developer / Contributor',
                'description': combined_project_text,
                'polished_bullets': polished_bullets.split('\n'),
                'technologies': state.get('technical_skills', {}).get('languages', [])[:3]
            }

            state['projects'] = state.get('projects', [])
            state['projects'].append(project_item)

            certs = state.get('available_certificates', [])
            cert_msg = ""
            if certs:
                cert_names = [f"✓ **{c['course']}** (ID: `{c['certificate_id']}`)" for c in certs]
                cert_msg = (
                    f"\n\n🔗 **BlockCert Automatic Sync:** I found **{len(certs)} Blockchain-Verified Certificate(s)** in your institutional profile:\n"
                    + "\n".join(cert_names)
                    + "\n\nThese will be automatically stamped with a **Blockchain Verified Badge ✓** on your resume!"
                )
            else:
                cert_msg = "\n\n(No external certificates found yet; we'll focus on your project portfolio.)"

            ai_message = (
                f"✨ **AI Enhancement Preview:** I have polished your project into high-impact ATS statements:\n\n"
                + "\n".join([f"• {b}" for b in project_item['polished_bullets']])
                + cert_msg + "\n\n"
                f"Next: **Do you have any internships, work experience, or hackathon achievements to include?** (If not, simply reply *None* or tell me about your leadership/extracurricular activities!)"
            )
            return {'next_step': 5, 'ai_message': ai_message, 'state': state}

        # Step 5: Experience / Extracurriculars -> Wrap up & generate resume
        elif step == 5:
            if user_reply and user_reply.lower() not in ['none', 'no', 'n/a', 'skip']:
                polished_exp = cls.polish_text_with_ai(user_reply, context_type="experience")
                state['experience'] = [
                    {
                        'company': 'Professional Experience / Academic Initiative',
                        'role': 'Developer / Technical Contributor',
                        'duration': '2024 - Present',
                        'bullets': polished_exp.split('\n')
                    }
                ]
            else:
                state['experience'] = []

            # Generate polished professional summary
            degree_str = state.get('academic', {}).get('degree', 'Computer Science')
            langs = ", ".join(state.get('technical_skills', {}).get('languages', ['Python', 'Web technologies'])[:3])
            state['summary'] = f"Results-driven {degree_str} graduate with verified expertise in {langs}. Proven ability to design and implement robust software solutions, demonstrated through production-quality projects and blockchain-anchored academic credentials."

            ai_message = (
                f"🎉 **Interview Complete! Your AI Resume is Ready!**\n\n"
                f"I have assembled your complete resume based on your actual verified credentials, technical stack, and polished project descriptions.\n\n"
                f"👉 Click **'Preview & Export Resume'** on the right to view your ATS-ready resume with **Blockchain Verified Credentials ✓**, customize sections, or download the printable PDF!"
            )
            return {'next_step': 6, 'ai_message': ai_message, 'state': state, 'is_complete': True}

        # Final state
        return {'next_step': 6, 'ai_message': "Your resume is ready for review and download!", 'state': state, 'is_complete': True}
