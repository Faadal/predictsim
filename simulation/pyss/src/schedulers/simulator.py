#!/usr/bin/env python2.4

from base.prototype import JobSubmissionEvent, JobTerminationEvent, JobPredictionIsOverEvent
from base.prototype import ValidatingMachine
from base.event_queue import EventQueue
from common import CpuSnapshot, list_print

from easy_plus_plus_scheduler import EasyPlusPlusScheduler
from shrinking_easy_scheduler import ShrinkingEasyScheduler

import sys
import os

class Simulator(object):
    """
    Assumption 1: The simulation clock goes only forward. Specifically,
    an event on time t can only produce future events with time t' = t or t' > t.
    Assumption 2: self.jobs holds every job that was introduced to the simulation.
    """

    def __init__(self, jobs, num_processors, scheduler, output_swf, input_file):
        self.num_processors = num_processors
        self.jobs = jobs
        self.terminated_jobs=[]
        self.scheduler = scheduler
        self.time_of_last_job_submission = 0
        self.event_queue = EventQueue()
        self.output_swf = None

        self.machine = ValidatingMachine(num_processors=num_processors, event_queue=self.event_queue)

        self.event_queue.add_handler(JobSubmissionEvent, self.handle_submission_event)
        self.event_queue.add_handler(JobTerminationEvent, self.handle_termination_event)
        if(output_swf != None):
		self.output_swf = open(output_swf, 'w+')
		version = os.popen("git show -s --format=\"%h %ci\" HEAD").read().strip()
		self.output_swf.write("; Computer: Pyss Simulator ("+version+")\n")
		self.output_swf.write("; Preemption: No\n")
		self.output_swf.write("; MaxNodes: -1\n")
		self.output_swf.write("; MaxProcs: "+str(num_processors)+"\n")
		self.output_swf.write("; Note: input_file:"+str(input_file)+"\n")
		self.output_swf.write("; Note: scheduler:"+str(scheduler.__class__.__name__)+"\n")
		self.event_queue.add_handler(JobTerminationEvent, self.store_terminated_job)

        if isinstance(scheduler, EasyPlusPlusScheduler) or isinstance(scheduler, ShrinkingEasyScheduler):
            self.event_queue.add_handler(JobPredictionIsOverEvent, self.handle_prediction_event)
            
        for job in self.jobs:
            self.event_queue.add_event( JobSubmissionEvent(job.submit_time, job) )
        

    def handle_submission_event(self, event):
        assert isinstance(event, JobSubmissionEvent)
        self.time_of_last_job_submission = event.timestamp
        newEvents = self.scheduler.new_events_on_job_submission(event.job, event.timestamp)
        for event in newEvents:
            self.event_queue.add_event(event)

    def handle_termination_event(self, event):
        assert isinstance(event, JobTerminationEvent)
        newEvents = self.scheduler.new_events_on_job_termination(event.job, event.timestamp)
        self.terminated_jobs.append(event.job)
        for event in newEvents:
            self.event_queue.add_event(event)

    def store_terminated_job(self, event):
        assert isinstance(event, JobTerminationEvent)
        #1. Job Number
        self.output_swf.write(str(event.job.id))
        self.output_swf.write(" ")
        #2. Submit Time 
        self.output_swf.write(str(event.job.submit_time))
        self.output_swf.write(" ")
        #3. Wait Time
        self.output_swf.write(str(event.job.start_to_run_at_time - event.job.submit_time))
        self.output_swf.write(" ")
        #4. Run Time
        self.output_swf.write(str(event.job.actual_run_time))
        self.output_swf.write(" ")
        #5. Number of Allocated Processors
        self.output_swf.write(str(event.job.num_required_processors))
        self.output_swf.write(" ")
        #6. Average CPU Time Used
        self.output_swf.write("-1")
        self.output_swf.write(" ")
        #7. Used Memory
        self.output_swf.write("-1")
        self.output_swf.write(" ")
        #8. Requested Number of Processors.
        self.output_swf.write(str(event.job.num_required_processors))
        self.output_swf.write(" ")
        #9. Requested Time
        self.output_swf.write(str(event.job.user_estimated_run_time))
        self.output_swf.write(" ")
        #10. Requested Memory
        self.output_swf.write("-1")
        self.output_swf.write(" ")
        #11. Status. This field is meaningless for models, so would be -1.
        self.output_swf.write("-1")
        self.output_swf.write(" ")
        #12. User ID
        self.output_swf.write(str(event.job.user_id))
        self.output_swf.write(" ")
        #13. Group ID
        self.output_swf.write("-1")
        self.output_swf.write(" ")
        #14. Executable (Application) Number
        self.output_swf.write("-1")
        self.output_swf.write(" ")
        #15. Queue Number
        self.output_swf.write("-1")
        self.output_swf.write(" ")
        #16. Partition Number
        self.output_swf.write("-1")
        self.output_swf.write(" ")
        #17. Preceding Job Number
        self.output_swf.write("-1")
        self.output_swf.write(" ")
        #18. Think Time
        self.output_swf.write("-1")
        self.output_swf.write("\n")

    def handle_prediction_event(self, event):
        assert isinstance(event, JobPredictionIsOverEvent)
        newEvents = self.scheduler.new_events_on_job_under_prediction(event.job, event.timestamp)
        for event in newEvents:
            self.event_queue.add_event(event)

            
    def run(self):
        while not self.event_queue.is_empty:
            self.event_queue.advance()

def run_simulator(num_processors, jobs, scheduler, output_swf=None, input_file=None, no_stats=False):
    simulator = Simulator(jobs, num_processors, scheduler, output_swf, input_file)
    simulator.run()
    if(not no_stats):
	print_simulator_stats(simulator)
    return simulator

def print_simulator_stats(simulator):
    simulator.scheduler.cpu_snapshot._restore_old_slices()
    # simulator.scheduler.cpu_snapshot.printCpuSlices()
    print_statistics(simulator.terminated_jobs, simulator.time_of_last_job_submission)

# increasing order 
by_finish_time_sort_key   = (
    lambda job : job.finish_time
)

# decreasing order   
#sort by: bounded slow down == max(1, (float(wait_time + run_time)/ max(run_time, 10))) 
by_bounded_slow_down_sort_key = (
    lambda job : -max(1, (float(job.start_to_run_at_time - job.submit_time + job.actual_run_time)/max(job.actual_run_time, 10)))
)

    
def print_statistics(jobs, time_of_last_job_submission):
    assert jobs is not None, "Input file is probably empty."
    
    sum_waits     = 0
    sum_run_times = 0
    sum_slowdowns           = 0.0
    sum_bounded_slowdowns   = 0.0
    sum_estimated_slowdowns = 0.0
    sum_tail_slowdowns      = 0.0

    
    counter = tmp_counter = tail_counter = 0
    
    size = len(jobs)
    precent_of_size = int(size / 100)
    
    for job in sorted(jobs, key=by_finish_time_sort_key):
        
        tmp_counter += 1

        if job.user_estimated_run_time == 1 and job.num_required_processors == 1: # ignore tiny jobs for the statistics
            size -= 1
            precent_of_size = int(size / 100)
            continue
        
        if size >= 100 and tmp_counter <= precent_of_size:
            continue
        
        if job.finish_time > time_of_last_job_submission:
            break 
        
        counter += 1
        
        wait_time = float(job.start_to_run_at_time - job.submit_time)
        run_time  = float(job.actual_run_time)
        estimated_run_time = float(job.user_estimated_run_time)


        sum_waits += wait_time
        sum_run_times += run_time
        sum_slowdowns += float(wait_time + run_time) / run_time
        sum_bounded_slowdowns   += max(1, (float(wait_time + run_time)/ max(run_time, 10))) 
        sum_estimated_slowdowns += float(wait_time + run_time) / estimated_run_time

        if max(1, (float(wait_time + run_time)/ max(run_time, 10))) >= 3:
            tail_counter += 1
            sum_tail_slowdowns += max(1, (float(wait_time + run_time)/ max(run_time, 10)))
            
    sum_percentile_tail_slowdowns = 0.0
    percentile_counter = counter
    
    for job in sorted(jobs, key=by_bounded_slow_down_sort_key):
        wait_time = float(job.start_to_run_at_time - job.submit_time)
        run_time  = float(job.actual_run_time)
        sum_percentile_tail_slowdowns += float(wait_time + run_time) / run_time
        percentile_counter -= 1 # decreamenting the counter 
        if percentile_counter < (0.9 * counter):
            break
        
        
        
    print
    print "STATISTICS: "
    
    print "Wait (Tw) [minutes]: ", float(sum_waits) / (60 * max(counter, 1))

    print "Response time (Tw+Tr) [minutes]: ", float(sum_waits + sum_run_times) / (60 * max(counter, 1))
    
    print "Slowdown (Tw+Tr) / Tr: ", sum_slowdowns / max(counter, 1)

    print "Bounded slowdown max(1, (Tw+Tr) / max(10, Tr): ", sum_bounded_slowdowns / max(counter, 1)
    
    print "Estimated slowdown (Tw+Tr) / Te: ", sum_estimated_slowdowns / max(counter, 1)

    print "Tail slowdown (if bounded_sld >= 3): ", sum_tail_slowdowns / max(tail_counter, 1)
    print "   Number of jobs in the tail: ", tail_counter

    print "Tail Percentile (the top 10% sld): ", sum_percentile_tail_slowdowns / max(counter - percentile_counter + 1, 1)    
    
    print "Total Number of jobs: ", size
    
    print "Number of jobs used to calculate statistics: ", counter
    print

