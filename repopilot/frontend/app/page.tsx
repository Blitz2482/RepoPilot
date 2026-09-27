"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Rocket, Loader2 } from "lucide-react";

export default function SubmitScreen() {
  const router = useRouter();
  const [repoUrl, setRepoUrl] = useState("");
  const [role, setRole] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  // Validate that the URL is a proper GitHub URL
  const isValidUrl = repoUrl.trim().startsWith("https://github.com/") && repoUrl.trim().length > 19;
  const isFormValid = isValidUrl && role !== "";

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isFormValid) return;

    setIsLoading(true);
    setError("");

    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

      const response = await fetch(`${apiUrl}/api/repos`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          repo_url: repoUrl.trim(),
          role: role,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to submit repository. Is the backend running?");
      }

      const data = await response.json();

      // Route to the live analysis screen with the new job ID
      router.push(`/analysis/${data.job_id}`);
    } catch (err) {
      console.error("Submission error:", err);
      setError(err instanceof Error ? err.message : "An unknown error occurred");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Subtle Premium Glow Effect */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-[#0F62FE]/5 rounded-full blur-3xl -z-10" />

      <Card className="w-full max-w-md shadow-xl border border-gray-200 bg-white/80 backdrop-blur-sm border-t-4 border-t-[#0F62FE]">
        <CardHeader className="space-y-1 text-center">
          <div className="flex justify-center mb-2">
            <div className="bg-[#0F62FE]/10 p-3 rounded-full">
              <Rocket className="h-8 w-8 text-[#0F62FE]" />
            </div>
          </div>
          <CardTitle className="text-2xl font-bold text-gray-900">RepoPilot</CardTitle>
          <CardDescription className="text-gray-600">
            AI-powered developer onboarding. Paste a GitHub URL to begin.
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* GitHub URL Input */}
            <div className="space-y-2">
              <label htmlFor="repoUrl" className="text-sm font-medium text-gray-700">
                GitHub Repository URL
              </label>
              <div className="relative">
                <div className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm">
                  🔗
                </div>
                <Input
                  id="repoUrl"
                  placeholder="https://github.com/owner/repo"
                  value={repoUrl}
                  onChange={(e) => {
                    setRepoUrl(e.target.value);
                    if (error) setError("");
                  }}
                  className={`pl-10 ${!isValidUrl && repoUrl.length > 0 ? "border-red-500 focus-visible:ring-red-500" : ""}`}
                />
              </div>
              {!isValidUrl && repoUrl.length > 0 && (
                <p className="text-xs text-red-500">Please enter a valid https://github.com/... URL</p>
              )}
            </div>

            {/* Role Dropdown */}
            <div className="space-y-2">
              <label htmlFor="role" className="text-sm font-medium text-gray-700">
                Your Developer Role
              </label>
              <Select
                value={role}
                onValueChange={(value) => value && setRole(value)}
              >
                <SelectTrigger className="w-full">
                  <SelectValue placeholder="Select your role..." />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Backend">Backend</SelectItem>
                  <SelectItem value="Frontend">Frontend</SelectItem>
                  <SelectItem value="Full-Stack">Full-Stack</SelectItem>
                  <SelectItem value="Data">Data</SelectItem>
                  <SelectItem value="DevOps">DevOps</SelectItem>
                  <SelectItem value="QA">QA</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-md text-sm animate-in fade-in slide-in-from-top-1">
                {error}
              </div>
            )}

            {/* Submit Button */}
            <Button
              type="submit"
              className="w-full bg-[#0F62FE] hover:bg-[#0353E9] text-white font-semibold transition-colors shadow-md"
              disabled={!isFormValid || isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Analyzing Repository...
                </>
              ) : (
                "Analyze Repository"
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </main>
  );
}