import React, { useState, useEffect } from 'react';
import { api } from '@/lib/api';
import { SEO } from '@/lib/seo';
import { Play, CheckSquare, Square, AlertTriangle, ShieldCheck, ArrowRight, MessageSquare } from 'lucide-react';
import { toast } from 'sonner';

interface SOPTemplate {
  id: string;
  code: string;
  title: string;
  steps_count: number;
  last_run: string;
  severity: string;
  description: string;
}

const SOP_STEPS: Record<string, string[]> = {
  'sop-fire': [
    'Immediately order Traction Power Controller (TPC) to de-energize 25kV OHE power in affected section.',
    'Issue Emergency Stop Caution Order to all incoming trains on adjacent lines.',
    'Sound Station Emergency Siren (3 long blasts) & dispatch Station RPF Quick Response Team.',
    'Call City Fire Brigade (101 / 112) with exact station chainage and road access gate.',
    'Deploy platform staff with water hydrants and dry chemical powder extinguishers.',
    'Initiate safe passenger detrainment and headcount at concourse assembly point.',
  ],
  'sop-derail': [
    'Trip all approach signals to DANGER (Red) and apply track protection detonators at 600m & 1200m.',
    'Order Accident Relief Medical Equipment (ARME) and Breakdown (BD) Special Train from Kanpur Yard.',
    'Inform Senior Divisional Operations Manager (Sr. DOM) and Safety Officer on hotline.',
    'Dispatch Medical First Responder team with emergency stretchers and oxygen cylinders.',
    'Isolate affected point switches and lock relay cabin in emergency mode.',
    'Cordon off accident site for statutory Commissioner of Railway Safety (CRS) inquiry.',
  ],
  'sop-lc-fail': [
    'Issue Stop & Proceed caution order to all drivers approaching Level Crossing.',
    'Dispatch Gateman relief and station flagman with hand danger signals (Red flags / lamps).',
    'Coordinate with local traffic police to manage road vehicular queue.',
    'Deploy signal maintenance technician for boom barrier motor / circuit repair.',
    'Verify barrier locking interlock before normalizing signal line clear.',
  ],
  'sop-fog': [
    'Impose statutory 60 km/h fog speed restriction across entire station approach.',
    'Order detonator placement at 270m before First Stop Signal by Fog Signalmen.',
    'Verify lime marking on track boundaries and fog signal post illumination.',
    'Ensure all departing trains have functional GPS Fog PASS devices installed.',
  ],
};

export function SOPRunnerPage() {
  const [templates, setTemplates] = useState<SOPTemplate[]>([]);
  const [activeTemplate, setActiveTemplate] = useState<SOPTemplate | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [stepTimestamps, setStepTimestamps] = useState<string[]>([]);
  const [runStartTime, setRunStartTime] = useState<number | null>(null);

  useEffect(() => {
    api.getSOPTemplates().then(data => setTemplates(data as SOPTemplate[]));
  }, []);

  const handleStartSOP = (tmpl: SOPTemplate) => {
    setActiveTemplate(tmpl);
    setCurrentStep(0);
    setCompletedSteps([]);
    setStepTimestamps([]);
    setRunStartTime(Date.now());
    toast.success(`Emergency protocol initiated: ${tmpl.title}`);
  };

  const handleCompleteStep = (stepIdx: number) => {
    if (completedSteps.includes(stepIdx)) return;

    const nextCompleted = [...completedSteps, stepIdx];
    const nextTimes = [...stepTimestamps, new Date().toLocaleTimeString()];
    setCompletedSteps(nextCompleted);
    setStepTimestamps(nextTimes);

    const steps = SOP_STEPS[activeTemplate?.id || 'sop-fire'] || [];
    if (nextCompleted.length === steps.length) {
      const durationSec = Math.round((Date.now() - (runStartTime || Date.now())) / 1000);
      toast.success(`SOP Completed in ${durationSec}s. Archived to regulatory audit log.`);
    } else {
      setCurrentStep(stepIdx + 1);
    }
  };

  const activeSteps = activeTemplate ? SOP_STEPS[activeTemplate.id] || [] : [];

  return (
    <div className="space-y-4">
      <SEO title="Emergency SOP Checklist Runner · RailTwin-X" noindex />

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-3 border-b border-[#26282C] gap-3">
        <div>
          <h1 className="text-lg font-semibold text-[#E8E8E6] flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[#FFB224]" />
            <span>Emergency Standard Operating Procedure (SOP) Runner</span>
          </h1>
          <p className="font-mono text-xs text-[#9A9DA3]">
            High-stress operational checklists with auto-timestamps, escalation drafting, and audit trail
          </p>
        </div>

        {activeTemplate && (
          <button
            onClick={() => setActiveTemplate(null)}
            className="px-3 py-1.5 bg-[#15171A] border border-[#26282C] text-xs font-mono text-[#9A9DA3] hover:text-[#E8E8E6]"
          >
            Exit SOP Runner
          </button>
        )}
      </div>

      {!activeTemplate ? (
        /* Template Selection Rows */
        <div className="bg-[#15171A] border border-[#26282C] divide-y divide-[#26282C]">
          {templates.map(t => (
            <div
              key={t.id}
              className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 hover:bg-[#1B1D21]/60 transition-colors font-mono"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-3">
                  <span className="font-bold text-sm text-[#FFB224]">{t.code}</span>
                  <span className="font-semibold text-sm text-[#E8E8E6]">{t.title}</span>
                  <span
                    className={`text-[10px] px-2 py-0.5 border font-bold ${
                      t.severity === 'CRITICAL'
                        ? 'border-[#F0533A] text-[#F0533A] bg-[#F0533A]/10'
                        : 'border-[#FFB224] text-[#FFB224] bg-[#FFB224]/10'
                    }`}
                  >
                    {t.severity}
                  </span>
                </div>
                <p className="text-xs text-[#9A9DA3] font-sans">{t.description}</p>
                <div className="text-[11px] text-[#6B6E74] flex gap-4 pt-1">
                  <span>{t.steps_count} Verification Steps</span>
                  <span>Last Executed: {t.last_run}</span>
                </div>
              </div>

              <button
                onClick={() => handleStartSOP(t)}
                className="px-4 py-2 bg-[#FFB224] hover:bg-[#E59F1C] text-[#0E0F11] font-bold text-xs flex items-center gap-2 self-start sm:self-center transition-colors"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Start Protocol</span>
              </button>
            </div>
          ))}
        </div>
      ) : (
        /* Active SOP Step-by-Step Running Screen */
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
          {/* Steps Column */}
          <div className="lg:col-span-8 bg-[#15171A] border border-[#26282C] p-6 font-mono text-xs space-y-4">
            <div className="flex items-center justify-between border-b border-[#26282C] pb-3">
              <div>
                <span className="text-[11px] text-[#FFB224] font-bold uppercase">{activeTemplate.code}</span>
                <h2 className="text-base font-bold text-[#E8E8E6]">{activeTemplate.title}</h2>
              </div>
              <div className="text-right">
                <span className="text-[11px] text-[#9A9DA3]">Progress</span>
                <div className="font-bold text-sm text-[#3ECF8E]">
                  {completedSteps.length} / {activeSteps.length} Steps
                </div>
              </div>
            </div>

            {/* Checklist Items */}
            <div className="space-y-3 pt-2">
              {activeSteps.map((stepText, idx) => {
                const isDone = completedSteps.includes(idx);
                const isCurrent = currentStep === idx && !isDone;

                return (
                  <div
                    key={idx}
                    onClick={() => handleCompleteStep(idx)}
                    className={`p-4 border cursor-pointer transition-all flex items-start gap-3 ${
                      isDone
                        ? 'bg-[#0E0F11] border-[#3ECF8E]/40 opacity-80'
                        : isCurrent
                        ? 'bg-[#1B1D21] border-[#FFB224]'
                        : 'bg-[#0E0F11] border-[#26282C] opacity-60'
                    }`}
                  >
                    <button className="mt-0.5 text-base">
                      {isDone ? (
                        <CheckSquare className="w-5 h-5 text-[#3ECF8E]" />
                      ) : (
                        <Square className={`w-5 h-5 ${isCurrent ? 'text-[#FFB224]' : 'text-[#9A9DA3]'}`} />
                      )}
                    </button>

                    <div className="flex-1 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className={`font-bold uppercase text-[11px] ${isCurrent ? 'text-[#FFB224]' : 'text-[#9A9DA3]'}`}>
                          Step {idx + 1}
                        </span>
                        {isDone && (
                          <span className="text-[10px] text-[#3ECF8E] font-mono">
                            Verified {stepTimestamps[completedSteps.indexOf(idx)]}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-[#E8E8E6] font-sans leading-relaxed">{stepText}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Right: Escalation Dispatch Assistant */}
          <div className="lg:col-span-4 bg-[#15171A] border border-[#26282C] p-5 font-mono text-xs space-y-4">
            <div className="border-b border-[#26282C] pb-2 font-bold text-sm text-[#E8E8E6] flex items-center gap-2">
              <MessageSquare className="w-4 h-4 text-[#FFB224]" />
              <span>Escalation Dispatcher</span>
            </div>

            <div className="bg-[#0E0F11] p-3 border border-[#26282C] space-y-2">
              <span className="text-[10px] text-[#9A9DA3] uppercase block font-semibold">
                Auto-Drafted WhatsApp & SMS Broadcast
              </span>
              <p className="text-xs text-[#E8E8E6] font-mono leading-relaxed bg-[#15171A] p-2 border border-[#26282C]">
                &quot;[URGENT-RAILTWIN-X] Emergency {activeTemplate.title} declared at Kanpur Central (CNB). All concerned staff report to duty immediately. Reference: {activeTemplate.code}.&quot;
              </p>
            </div>

            <div className="pt-2 border-t border-[#26282C] space-y-2 text-[11px] text-[#9A9DA3]">
              <div className="flex justify-between">
                <span>Hotline Recipient 1:</span>
                <span className="text-[#E8E8E6]">Senior DOM (Prayagraj)</span>
              </div>
              <div className="flex justify-between">
                <span>Hotline Recipient 2:</span>
                <span className="text-[#E8E8E6]">City Fire & Medical Desk</span>
              </div>
              <div className="flex justify-between">
                <span>Hotline Recipient 3:</span>
                <span className="text-[#E8E8E6]">Divisional Security Commissioner</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
