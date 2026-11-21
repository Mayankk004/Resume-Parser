import { render, screen } from "@testing-library/react";
import CandidateProfile from "./components/CandidateProfile";

test("renders candidate profile with matched and missing skill badges", () => {
  const sampleResume = {
    id: 1,
    name: "Jane Doe",
    email: "jane@example.com",
    phone_number: "+1 555-0199",
    gpa: "3.9",
    model_type: "gemini",
    skills: {
      Languages: ["Python", "TypeScript"],
      Frameworks: ["FastAPI", "React"],
    },
    work_experience: [
      { Company: "TechCorp", Position: "Software Engineer", Duration: "2022-2025" },
    ],
    education: [{ Degree: "B.S. Computer Science", Institution: "MIT", Year: "2022" }],
    projects: [{ Name: "AI Search", Description: "Built semantic RAG search." }],
    certifications: ["AWS Solutions Architect"],
  };

  render(
    <CandidateProfile
      resume={sampleResume}
      matchMeta={{
        match_score: 91.5,
        semantic_score: 86.0,
        matched_skills: ["Python", "FastAPI"],
        missing_skills: ["Kubernetes"],
        matched_criteria: ["Python", "FastAPI"],
      }}
    />
  );

  expect(screen.getByText("Jane Doe")).toBeInTheDocument();
  expect(screen.getByText("91.5% Match")).toBeInTheDocument();
  expect(screen.getAllByText("FastAPI").length).toBeGreaterThanOrEqual(2);
  expect(screen.getByText("Kubernetes")).toBeInTheDocument();
  expect(screen.getByText("TechCorp")).toBeInTheDocument();
  expect(screen.getByText("AWS Solutions Architect")).toBeInTheDocument();
});
